# Please read the accompanying license document and readme file
import datetime
import time
import mutagen.flac
import os
import shutil
from PIL import Image
import subprocess
import threading
import sys
import time
import datetime
from mpris_server import Track, Album
from list_info import TextItem, TrackItem, compare_track_items
from pathvalidate import sanitize_filepath

CD = "CD"
HDD = "HDD"

NOT_APPLICABLE = "NOT_APPLICABLE"
RIP_FETCHING = "RIP_FETCHING"
RIP_IN_PROGRESS = "RIP_IN_PROGRESS"
RIP_COMPLETE = "RIP_COMPLETE"

def format_seconds(seconds):
    # Create a timedelta object from seconds
    delta = datetime.timedelta(seconds=seconds)
    
    # Extract total hours, minutes, seconds, and milliseconds
    total_hours, remainder = divmod(delta.total_seconds(), 3600)
    total_minutes, total_seconds = divmod(remainder, 60)
    milliseconds = (total_seconds - int(total_seconds)) * 1000
    
    # Format as HH:MM:SS.mmm
    formatted_time = f"{int(total_hours):02}:{int(total_minutes):02}:{int(total_seconds):02}.{int(milliseconds):03}"
    
    return formatted_time

class TrackProperties:
    album_manager = None
    trackNumber = 0
    artist = ""
    title = ""
    path = ""
    picture = None
    length = 0
    current_time = 0
    
    change_lock = False
    play_lock = False
    change_pending = False
    change_staged = False
    play_pending = False
    paused = False

    def get_track_data(self, album, track_number):
        return Track(album=album,art_url=None,artists=[self.artist],comments=None,disc_number=None,length=self.length,name=self.title,track_number=track_number)
    
    def set_track_number(self, track_number):
        if self.trackNumber != track_number:
            self.trackNumber = track_number
            self.change_staged = True
            
    def set_artist(self, artist):
        if self.artist != artist:
            self.artist = artist
            self.change_staged = True
            
    def set_title(self, title):
        if self.title != title:
            self.title = title
            self.change_staged = True
            
    def set_picture(self, picture):
        self.picture = picture
        self.change_staged = True
        
    def apply_changes(self):
        if self.change_staged == True:
            self.change_pending = True
            self.change_staged = False
            self.catch_up()

    def catch_up(self):
        if self.play_lock == False and self.change_lock == False and self.change_pending == True:
            self.apply_pending_changes()
        elif self.play_lock == False and self.change_lock == False and self.play_pending == True:
            self.play()
        
    
    def clear_pending_changes(self):
        self.change_lock = False
        self.change_pending = False
        self.change_staged = False

    def move_file(self, src, dst):
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # Move the file to the new location, overwriting if necessary
        shutil.move(src, dst)

    def is_awaiting_rip(self):
        return (self.path.endswith(".wav") and self.can_play_immediately() == False)
    
    def apply_pending_changes(self):
        if self.path.endswith(".wav"):
            print("Nothing for now, wav file")
        elif self.path.endswith(".flac") or self.path.endswith(".fla"):            
            track_num_as_str = str(self.trackNumber)

            if self.trackNumber < 10:
                track_num_as_str = "0" + track_num_as_str      
      
            base_path = self.album_manager.music_dir

            new_path = base_path + self.album_manager.album.artist.replace("/", "-") + "/" + self.album_manager.album.title + "/" + track_num_as_str + ". " + self.title + ".flac"

            if new_path != self.path:
                self.move_file(self.path, new_path)
                self.path = new_path
        
            audio = mutagen.flac.FLAC(self.path)
            audio.tags['ARTIST'] = self.artist
            audio.tags['TITLE'] = self.title
            audio.tags['ALBUM'] = self.album_manager.album.title
            audio.tags['ALBUMARTIST'] = self.album_manager.album.artist
            audio.tags['TRACKNUMBER'] = track_num_as_str

            total_as_str = str(len(self.album_manager.album.tracks))

            if len(self.album_manager.album.tracks) < 10:
                total_as_str = "0" + total_as_str

            audio.tags['TRACKTOTAL'] = total_as_str
        

            audio.save()

            if self.picture is not None:
                audio = mutagen.flac.FLAC(self.path)

                audio.clear_pictures()

                audio.save()

                audio = mutagen.flac.FLAC(self.path)

                # Add the Picture object to the FLAC file's metadata
                audio.add_picture(self.picture)

                # Save the FLAC file
                audio.save()    
            

        
        self.clear_pending_changes()

    def save_first_available_cover_image(self):
        audio = mutagen.flac.FLAC(self.path)

        if audio.pictures:
            for picture in audio.pictures:
                if picture.type == 3:  # COVER_FRONT
                    image_data = picture.data
                    with open("./cache/temp.png", "wb") as f:
                        f.write(image_data)
                    return True

        return False
        
    def can_play_immediately(self):
        if self.path.endswith(".wav") == True:
            if os.path.exists(self.path) == False:
                return False
            elif os.path.getsize(self.path) < 1048576:
                return False

        return True 

    def play_if_possible(self):        
        if self.can_play_immediately() == True:
            self.play()
        else:
            self.playback_timer = threading.Timer(2.0, self.play_if_possible)
            self.playback_timer.start()

    def play(self):
        self.current_time = 0
        self.paused = False
        if self.change_lock == True:
            self.play_pending = True
        else:
            self.play_pending = False
            self.play_lock = True

            if hasattr(self, "playback_timer"):
                self.playback_timer.cancel()
            if hasattr(self, "playback_thread"):
                self.playback_thread.join()

            if self.can_play_immediately() == True:
                self.playback_thread = threading.Thread(target=self.do_playback)
                self.playback_thread.start()
            else:
                self.playback_timer = threading.Timer(2.0, self.play_if_possible)
                self.playback_timer.start()
            
    
    
    def pause(self):
        self.current_time = (time.time() - self.last_play_timestamp) + self.current_time
        self.paused = True
        if hasattr(self, "playback_process"):
            self.playback_process.terminate()

        if hasattr(self, "playback_thread"):
            self.playback_thread.join()
        self.album_manager.on_album_data_change()
                        
        
    def resume(self):
        self.paused = False
        self.playback_thread = threading.Thread(target=self.do_playback)
        self.playback_thread.start()
        self.album_manager.on_album_data_change()
    
    def stop(self):
        if self.play_lock == True:
            if hasattr(self, "playback_process"):
                self.playback_process.terminate()

            if hasattr(self, "playback_thread"):
                self.playback_thread.join()

            if hasattr(self, "playback_timer"):
                self.playback_timer.cancel()
                        
            self.play_lock = False           
            
     
    def do_playback(self):
        # todo trim by current time here
        if self.current_time > 0:
            args = ["play", self.path, "trim", format_seconds(self.current_time)]
        else:
            args = ["play", self.path]
    
        self.playback_process = subprocess.Popen(args)
        self.last_play_timestamp = time.time()

        self.playback_process.wait()
        
        if self.paused == False:
            self.play_lock = False
            self.album_manager.on_track_complete()
        
        
    def callback(stdout, stderr):
        # Process the output and error streams as needed
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")
    
    
class AlbumProperties:
    tracks = []
    folder = ""

    picture = None
    current_playing_index = -1
    next_playing_index = -1
    ripping_track = 0
    ripping_process = None
    tagging_thread = None
    fetch_cd_info_thread = None
    is_compilation_album = False
    source = HDD
    list_model = None
    ripping_status = NOT_APPLICABLE
    
    def __init__(self, list_model):
        now = datetime.datetime.now()
        unix_timestamp = int(now.timestamp())
        unix_timestamp_str = str(unix_timestamp)

        self.artist = "Unkown Artist " + unix_timestamp_str
        self.title = "Unknown Album " + unix_timestamp_str

        self.list_model = list_model

    def get_album_data(self):
        return Album(art_url=None,artists=[self.artist],name=self.title)

    def get_current_track_data(self):
        if self.current_playing_index > 0 and self.current_playing_index < len(self.tracks):
            return self.get_track_data(self.current_playing_index + 1)

        return None

    def get_previous_track_data(self):
        previous_index = self.current_playing_index - 1

        if previous_index < 0:
            previous_index = len(self.tracks) - 1

        if previous_index >= len(self.tracks):
            previous_index = len(self.tracks) - 1

        return self.get_track_data(previous_index + 1)

    def get_next_track_data(self):
        next_index = self.current_playing_index + 1

        if next_index < 0:
            next_index = len(self.tracks) - 1

        if next_index >= len(self.tracks):
            next_index = len(self.tracks) - 1

        return self.get_track_data(next_index + 1)

    def get_track_data(self, track_number):
        track_index = track_number - 1
        
        if track_index < 0 or track_index >= len(self.tracks):
            return None

        self.tracks[track_index].get_track_data(self.get_album_data(),track_number)

    def move_file(self, src, dst):
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        # Move the file to the new location, overwriting if necessary
        shutil.move(src, dst)
        
    def set_artist(self, artist):
        if artist != self.artist:
            self.artist = artist
            for track in self.tracks:
                track.change_staged = True
            self.album_manager.on_album_data_change()

    def set_title(self, title):
        if title != self.title:
            self.title = title
            for track in self.tracks:
                track.change_staged = True
            self.album_manager.on_album_data_change()


    def get_first_available_cover_image_data(self):
        get_next = False
        i = 0

        print("GET IMAGE")

        while get_next == False and i < len(self.tracks):
            print("LOOPING")            
            get_next = self.tracks[i].save_first_available_cover_image()
            i = i + 1


        print("RETURNING")
        print(get_next)
        return get_next

    def populate_tracks_to_rip(self, tracks, fetch_cd_info, rip_callback_event):
        self.stop()
        num_tracks = len(tracks)
        self.tracks = []
        self.source = CD
        self_ripping_status = RIP_FETCHING        
                
        for i in range(num_tracks):
            track = TrackProperties()
            track.artist = "Unknown Artist"
            track.trackNumber = i + 1
            track.album_manager = self.album_manager
            
            ripping_track_as_str = str(track.trackNumber)
            if track.trackNumber < 10:
                ripping_track_as_str = "0" + ripping_track_as_str

            track.title = f"Track " + ripping_track_as_str

            track.path = f"./cache/track" + ripping_track_as_str + ".wav";
            track.length = tracks[i].seconds
            self.tracks.append(track)

        self.rip_callback_event = rip_callback_event
        self.ripv2_thread = threading.Thread(target=self.sync_rip)
        self.ripv2_thread.start()

        callback_event = threading.Event()
        self.fetch_cd_info_thread = threading.Thread(target=fetch_cd_info, args=(callback_event,))
        self.fetch_cd_info_thread.start()
        callback_event.wait()
        print("CB Event Set")
        self.ripping_status = RIP_IN_PROGRESS
        self.album_manager.on_album_data_change()
        self.album_manager.on_cd_fetch_complete()
        self.fetch_cd_info_thread.join()
        
        
    def sync_rip(self):
        self.ripping_track = self.ripping_track + 1
        
        if self.ripping_track <= len(self.tracks):
            if self.tracks[self.ripping_track - 1].is_awaiting_rip():                
                self.ripping_track_as_str = str(self.ripping_track)
                if self.ripping_track < 10:
                    self.ripping_track_as_str = "0" + self.ripping_track_as_str

                target_filename = "track" + self.ripping_track_as_str + ".wav";
                target_flac_filename = "track" + self.ripping_track_as_str + ".flac";
                args = ["cdparanoia", str(self.ripping_track), "./cache/" + target_filename]
                self.ripping_process = subprocess.Popen(args)
                return_code = self.ripping_process.wait()
                # if bad exit error from cdparanoia process above, exit
                if return_code == 0:
                    self.tag_and_store_track(self.ripping_track, "./cache/" + target_filename, "./cache/" + target_flac_filename)
                    self.sync_rip()
            else:
                self.sync_rip()
        else:
            for i in range(len(self.tracks)):
                if self.tracks[i].is_awaiting_rip():
                    self.ripping_track = i
                    self.sync_rip()
                    break

            self.ripping_process = None
            self.ripping_status = RIP_COMPLETE

            self.album_manager.on_album_rip_complete()

        
    def cancel_current_rip(self):
        if hasattr(self, "ripv2_thread") and self.ripping_process is not None:
            self.ripping_process.terminate()
            self.ripv2_thread.join()
            os.remove("./cache/track" + self.ripping_track_as_str + ".wav")
            self.ripping_process = None

    def request_rip_immediately(self, next_playing_index):
        if hasattr(self, "ripv2_thread") and hasattr(self, "ripping_process"):
            self.ripping_process.terminate()
            self.ripv2_thread.join()
            os.remove("./cache/track" + self.ripping_track_as_str + ".wav")
            self.ripping_process = None

        self.ripping_track = next_playing_index
        self.ripv2_thread = threading.Thread(target=self.sync_rip)
        self.ripv2_thread.start()
        
    def tag_and_store_track(self, track_num, track_wav_filename, track_flac_filename):
        self.tagging_thread = threading.Thread(target=self.do_tag_and_store, args=(track_num, track_wav_filename, track_flac_filename,))
        self.tagging_thread.start()

    def do_tag_and_store(self, track_num, track_wav_filename, track_flac_filename):
        # sample ffmpeg commmand:
        # ffmpeg -i input.wav -c:a flac output.flac
        args = ["ffmpeg", "-i", track_wav_filename, track_flac_filename]
        process = subprocess.Popen(args)
        process.wait()
        base_path = self.album_manager.music_dir

        base_path = base_path + self.artist + "/" + self.title + "/"
        self.tag_and_save_track(track_num, track_flac_filename, base_path)

    def set_picture(self, picture):
        for track in self.tracks:
            track.set_picture(picture)
    
    def populate_from_folder(self, folder):
        self.stop()
        self.folder = folder        
        self.tracks = []        
        filenames = next(os.walk(folder), (None, None, []))[2]  # [] if no file

        if folder.endswith("/") == False:
            folder = folder + "/"

        trackNumber = 0

        for fn in sorted(filenames):
            if fn.endswith(".flac") or fn.endswith("fla"):
                track = TrackProperties()
                track.path = folder + fn             
                trackNumber = trackNumber + 1                    
                audio = mutagen.flac.FLAC(track.path)
                track.length = audio.info.length
                tags = audio.tags
                track.trackNumber = trackNumber
                track.album_manager = self.album_manager
            

                if 'ARTIST' in tags and len(tags['ARTIST']) > 0:
                    track.artist = tags['ARTIST'][0]

                if 'TITLE' in tags and len(tags['TITLE']) > 0:                
                    track.title = tags['TITLE'][0]
                
                self.tracks.append(track)
                
                if 'ALBUM' in tags and len(tags['ALBUM']) > 0:
                    self.title = tags['ALBUM'][0]
                
                if 'ALBUMARTIST' in tags and len(tags['ALBUMARTIST']) > 0:
                    self.artist = tags['ALBUMARTIST'][0]

        self.album_manager.on_album_data_change()

        return self.get_first_available_cover_image_data()

    def tag_and_save_track(self, track_number, track_filename, track_destination_folder):
        # TODO move previously ripped tracks if destination folder has changed
        self.folder = track_destination_folder
 
        zi_track_number = track_number - 1

        track = self.tracks[zi_track_number]

        track_num_as_str = str(track_number)
        if track_number < 10:
            track_num_as_str = "0" + track_num_as_str

        fn_title = track.title.replace(":", " ")
  
        track_destination = track_destination_folder + track_num_as_str + ". " + fn_title + ".flac"
        track_destination = sanitize_filepath(track_destination)

        self.move_file(track_filename, track_destination)
        track.path = track_destination
        audio = mutagen.flac.FLAC(track.path)
        audio.tags['ARTIST'] = track.artist
        audio.tags['TITLE'] = track.title
        audio.tags['ALBUM'] = self.title
        audio.tags['ALBUMARTIST'] = self.artist
        audio.tags['TRACKNUMBER'] = track_num_as_str
        
        total_as_str = str(len(self.tracks))

        if len(self.tracks) < 10:
            total_as_str = "0" + total_as_str

        audio.tags['TRACKTOTAL'] = total_as_str
        audio.save()

        if self.picture is not None:
            audio = mutagen.flac.FLAC(track.path)

            audio.clear_pictures()

            audio.save()

            audio = mutagen.flac.FLAC(track.path)

            # Add the Picture object to the FLAC file's metadata
            audio.add_picture(self.picture)

            # Save the FLAC file
            audio.save()

    def apply_changes(self):
        for track in self.tracks:
            if self.is_compilation_album == False:
                track.set_artist(self.album_manager.album.artist)
            track.apply_changes()

    def set_album_cover(self, image_path):
        img = Image.open(image_path)

        bitDepth = 32

        if img.mode == "RGB":
            bitDepth = 24

        # Specify the new size (width, height)
        new_size = (500, 500)  # Replace with your desired size

        # Resize the image
        img_resized = img.resize(new_size)

        img_resized.save('./cache/temp.png', 'PNG')

        self.picture = mutagen.flac.Picture()
        self.picture.type = mutagen.id3.PictureType.COVER_FRONT
        self.picture.mime = 'image/png'
        self.picture.width = 500
        self.picture.height = 500
        self.picture.depth = bitDepth  # color depth

        # Assign the binary image data
        with open('./cache/temp.png', 'rb') as f:
            self.picture.data = f.read()

    def pause_or_resume(self):
        if self.tracks[self.current_playing_index].paused == True:
            self.tracks[self.current_playing_index].resume()
        else:
            self.tracks[self.current_playing_index].pause()
        return self.tracks[self.current_playing_index].paused    
     
    def get_play_lock(self):
        if self.current_playing_index < 0 or self.current_playing_index >= len(self.tracks):
            return False

        return self.tracks[self.current_playing_index].play_lock

    def get_paused(self):
        if self.current_playing_index < 0 or self.current_playing_index >= len(self.tracks):
            return False

        return self.tracks[self.current_playing_index].paused

    def get_current_track_artist(self):
        if self.current_playing_index < 0 or self.current_playing_index >= len(self.tracks):
            return "None"

        return self.tracks[self.current_playing_index].artist

    def get_current_track_title(self):
        if self.current_playing_index < 0 or self.current_playing_index >= len(self.tracks):
            return "None"

        return self.tracks[self.current_playing_index].title


    def request_track(self, next_playing_index):
        if next_playing_index >= 0 and next_playing_index < len(self.tracks):
            self.current_playing_index = next_playing_index            
            self.tracks[next_playing_index].play()
            self.next_playing_index = next_playing_index + 1
            self.album_manager.on_album_data_change()
            
    def request_track_immediately(self, next_playing_index):
        if next_playing_index >= 0 and next_playing_index < len(self.tracks):
            if self.tracks[next_playing_index].is_awaiting_rip():
                if (self.ripping_track - 1) != next_playing_index:
                    self.request_rip_immediately(next_playing_index)

        self.next_playing_index = next_playing_index
        
        if self.current_playing_index >= 0 and self.current_playing_index < len(self.tracks):
            self.tracks[self.current_playing_index].stop()       

    def fwd(self):
        if self.current_playing_index >= 0 and self.current_playing_index + 1 < len(self.tracks) and not self.tracks[self.current_playing_index].paused:
            self.request_track_immediately(self.current_playing_index + 1)

    def rew(self):
        if self.current_playing_index > 0 and self.current_playing_index < len(self.tracks) and not self.tracks[self.current_playing_index].paused:
            self.request_track_immediately(self.current_playing_index - 1)
            
    def stop(self):
        self.next_playing_index = -1
        
        if self.current_playing_index >= 0 and self.current_playing_index < len(self.tracks):
            self.tracks[self.current_playing_index].stop()       

    def on_track_complete(self):
        for track in self.tracks:
            track.catch_up()
        self.request_track(self.next_playing_index)
        self.album_manager.on_album_data_change()

    def get_ripping_summary(self):
        if self.ripping_status == RIP_IN_PROGRESS:
            return "Currently ripping CD..."
        elif self.ripping_status == RIP_COMPLETE:
            return "Rip Complete. You may now eject the CD."
        elif self.ripping_status == NOT_APPLICABLE:
            return "No rip in progress"
        
        

    def get_text_summary(self, paused, editable):
        print("Get Text Summary!")
        i = 0
        for track in self.tracks:
            old_item = self.list_model.get_item(i)

            new_item = TrackItem(artist=track.artist, title=track.title, editable=editable, track_number=i, playing = (i == self.current_playing_index))

            if i >= self.list_model.get_n_items():
                print("Add Item!")
                self.list_model.append(new_item)
            elif compare_track_items(old_item, new_item) == False:
                print("Update Item!")
                self.list_model.splice(i, 1, [new_item])

            i = i + 1

            

    def clean_up(self):
        self.stop()
        self.cancel_current_rip()
        self.tracks = []
        self.folder = ""

        self.picture = None
        self.current_playing_index = -1
        self.next_playing_index = -1
        self.ripping_track = 0
        self.artist = ""
        self.title = ""
        
        if self.tagging_thread is not None:
            self.tagging_thread.join()

        if self.fetch_cd_info_thread is not None:
            self.fetch_cd_info_thread.join()

        self.ripping_process = None
        self.tagging_thread = None
        self.fetch_cd_info_thread = None
        self.source = HDD
        self.list_model.remove_all()
        self.ripping_status = NOT_APPLICABLE

