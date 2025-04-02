# Please read the accompanying license document and readme file
import time
import sys
import os
import gi
import subprocess
import shutil
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Gsk, Gdk, Graphene
from pydbus import SystemBus
from pydbus import SessionBus
import pydbus
import yaml
# this will load libdiscid
import discid
import musicbrainzngs
import magic
import re
import mutagen.flac
import mutagen.id3
from PIL import Image

from musicmodels import TrackProperties
from musicmodels import AlbumProperties
from album_manager import AlbumManager

# Size of album image in UI
SIZE = 100

class AlbumImage(Gtk.Widget):
    x_scale = 1
    y_scale = 1

    is_mouse_down = True
    open_image_clicked = None

    def __init__(self):
        super().__init__()
        self.has_texture = False
        
    def add_texture(self, path):
        self.texture = Gdk.Texture.new_from_filename(path)
        self.has_texture = True
        self.queue_draw()

    def clear(self):
        self.texture = None
        self.has_texture = False
        self.queue_draw()

    def do_snapshot(self, s):
        if self.has_texture == True:
            self.x_scale = self.texture.get_width() / SIZE
            self.y_scale = self.texture.get_height() / SIZE

            rect = Graphene.Rect().init(0, 0, SIZE, SIZE)
            s.append_texture(self.texture, rect)

# Setup and bind functions for the factory
def setup(factory, list_item):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    list_item.smt_title_label = Gtk.Entry()
    box.append(list_item.smt_title_label)    
    list_item.set_child(box)
    list_item.smt_artist_label = Gtk.Entry()
    list_item.smt_artist_label.add_css_class("read-only")
    box.append(list_item.smt_artist_label)
    
    def on_artist_changed(entry):
        if AlbumManager().album is not None:
            track = AlbumManager().album.tracks[list_item.get_item().track_number]
            track.set_artist(list_item.smt_artist_label.get_buffer().get_text())

    list_item.smt_artist_label.connect('changed', on_artist_changed)

    def on_title_changed(entry):
        if AlbumManager().album is not None:
            track = AlbumManager().album.tracks[list_item.get_item().track_number]
            track.set_title(list_item.smt_title_label.get_buffer().get_text())
        

    list_item.smt_title_label.connect('changed', on_title_changed)
    #list_item.set_css_classes(["list-item-clear"])
    

def bind(factory, list_item):
    editable = list_item.get_item().editable
    playing = list_item.get_item().playing

    css_class = 'track-artist-play-mode'

    if editable == True:
        css_class = 'track-artist-edit-mode'
    elif playing == True:
        css_class = 'track-artist-play-mode-playing'

    list_item.smt_artist_label.get_buffer().set_text(list_item.get_item().artist, len(list_item.get_item().artist))
    list_item.smt_artist_label.set_editable(editable)
    list_item.smt_artist_label.set_sensitive(editable)
    list_item.smt_artist_label.set_css_classes([css_class])
    
    css_class = 'track-title-play-mode'

    if editable == True:
        css_class = 'track-title-edit-mode'
    elif playing == True:
        css_class = 'track-title-play-mode-playing'        

    list_item.smt_title_label.get_buffer().set_text(list_item.get_item().title, len(list_item.get_item().title))
    list_item.smt_title_label.set_editable(editable)
    list_item.smt_title_label.set_sensitive(editable)
    list_item.smt_title_label.set_css_classes([css_class])
    

class CDGui:
    paused = False
    editable = False

    def __init__(self, main_window):
        name = 'org.gnome.SessionManager'
        path = '/org/gnome/SessionManager'
        interface = 'org.gnome.SessionManager'

        method=['Inhibit', 'UnInhibit']
        self.name = name
        self.path = path
        self.interface_name = interface

        import dbus
        bus = dbus.SessionBus()
        devobj = bus.get_object(self.name, self.path)

        self.iface = dbus.Interface(devobj, self.interface_name)
        self._inhibit = self.iface.get_dbus_method('Inhibit')
        self._uninhibit = self.iface.get_dbus_method('Uninhibit')
        
        self.main_window = main_window

        self.album_source = "NONE"
        
        self.box1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.box2.set_margin_top(5)
        self.box2.set_margin_start(5)
        self.box2.set_margin_end(5)
        self.box2.set_margin_bottom(5)
        
        self.transport_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.transport_box.set_margin_top(5)
        self.transport_box.set_margin_start(5)
        self.transport_box.set_margin_end(5)
        self.transport_box.set_margin_bottom(5)
        self.transport_box.set_homogeneous(True)
        
        self.album_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.album_title_box.set_margin_top(5)
        self.album_title_box.set_margin_start(5)
        self.album_title_box.set_margin_end(5)
        self.album_title_box.set_margin_bottom(5)

        self.album_image_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.album_image_box.set_margin_top(5)
        self.album_image_box.set_margin_start(5)
        self.album_image_box.set_margin_end(5)
        self.album_image_box.set_margin_bottom(5)
        self.album_image_box.set_size_request(100, 100)
        
        self.album_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.album_text_box.set_margin_top(5)
        self.album_text_box.set_margin_start(5)
        self.album_text_box.set_margin_end(5)
        self.album_text_box.set_margin_bottom(5)
        self.album_text_box.set_size_request(260, 100)

        self.album_title_box.append(self.album_image_box)
        self.album_title_box.append(self.album_text_box)
        
        self.status_label = Gtk.Label(label="No Music Loaded")
        self.status_label.set_css_classes(['status-label'])        
        self.box1.append(self.status_label)

        self.box1.append(self.album_title_box)
        self.box1.append(self.box2)  # Put vert box in that box
        self.box1.append(self.transport_box)  # And another one, empty for now

        self.rew_button = Gtk.Button(label="⏮︎")
        self.rew_button.set_css_classes(['transport-button-small'])
        self.rew_button.connect('clicked', self.rewClicked)
        self.transport_box.append(self.rew_button)
                
        self.play_button = Gtk.Button(label="▶")
        self.play_button.connect('clicked', self.playClicked)
        self.play_button.set_css_classes(['transport-button-large'])
        self.transport_box.append(self.play_button)

        self.fwd_button = Gtk.Button(label="⏭︎")
        self.fwd_button.set_css_classes(['transport-button-small'])
        
        self.fwd_button.connect('clicked', self.fwd_clicked)
        self.transport_box.append(self.fwd_button)

        self.scrolledWindowA = Gtk.ScrolledWindow()
        self.scrolledWindowA.set_size_request(width=300,height=400)
        viewport = Gtk.Viewport()
        
        self.image_preview = AlbumImage()
        
        self.image_button = Gtk.Button()
        self.image_button.connect('clicked', self.open_image_clicked)
        self.image_button.set_child(self.image_preview)
        self.image_button.set_css_classes(['image-button'])
        self.image_button.set_size_request(100, 100)
        self.album_image_box.append(self.image_button)

        self.albumTitleEntry = Gtk.Entry()
        self.albumTitleEntry.set_css_classes(['album-title-play-mode'])
        self.albumTitleEntry.set_editable(False)
        self.albumTitleEntry.connect('changed', self.albumTitleEntryChanged)
        self.album_text_box.append(self.albumTitleEntry)

        self.albumArtistEntry = Gtk.Entry()
        self.albumArtistEntry.set_css_classes(['album-artist-play-mode'])
        self.albumArtistEntry.set_editable(False)
        self.albumArtistEntry.connect('changed', self.albumArtistEntryChanged)
        self.album_text_box.append(self.albumArtistEntry)

        self.open_dialog = Gtk.FileDialog.new()
        self.open_dialog.set_title("Select")

        # Create a factory
        factory = Gtk.SignalListItemFactory()

        factory.connect("setup", setup)
        factory.connect("bind", bind)

        self.tracks_list_selection = Gtk.SingleSelection(model=AlbumManager().list_model)
        self.tracks_list_view = Gtk.ListView.new(self.tracks_list_selection, factory)
        self.tracks_list_view.connect('activate', self.on_tracks_list_view_activate)
        
        viewport.set_child(self.tracks_list_view)
        self.scrolledWindowA.set_child(viewport)
        self.box2.append(self.scrolledWindowA)
        

        self.open_dialog = Gtk.FileDialog.new()
        self.open_dialog.set_title("Select a File")

    def playClicked(self, button):
        self.do_play()
    
    def do_play(self):
        if AlbumManager().album.get_play_lock() == True:
            self.pause_or_resume()
        else:
            self.inhibitCookie = self._inhibit("super_music_tools", 0, "Prevent system sleep during playback", 4)

            AlbumManager().album.request_track(0)
            self.main_window.mpris_event_handler.on_playback()
            self.play_button.set_label("❚❚")

        
    def clear_cache_directory(self):
        folder = './cache'
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    def load_cd(self, callback_event):
        self.status_label.set_label("Loading CD...")
        self.inhibitCookie = self._inhibit("super_music_tools", 0, "Prevent system sleep during playback", 4)
        self.clear_cache_directory()
        self.requested_track = 1
        self.ripping_track  = 0
        self.disc = discid.read()
        AlbumManager().populate_tracks_to_rip(self.disc.tracks, self.fetch_cd_info, callback_event)
    
    def fwd_clicked(self, button):
        self.do_next()
            
    def do_next(self):
        AlbumManager().album.fwd()
        self.main_window.mpris_event_handler.on_playback()
        
    def rewClicked(self, button):
        self.do_previous()
    
    def do_previous(self):
        AlbumManager().album.rew()
        self.main_window.mpris_event_handler.on_playback()
        
    def pause_or_resume(self):
        print("Pause or resume!!!")
        self.paused = AlbumManager().album.pause_or_resume()

        if self.paused:
            print("Paused!!!")
        
            self.play_button.set_label("▶")
            self.main_window.mpris_event_handler.on_playpause()
        else:
            print("Not Paused!!!")
        
            self.play_button.set_label("❚❚")
            self.main_window.mpris_event_handler.on_playback()

    def reset(self):
        self.play_button.set_label("▶")
        self.clear_image()

    def do_stop(self):   
        AlbumManager().album.stop()
        self.reset()
        self.main_window.mpris_event_handler.on_ended()

    def toggle_edit_mode(self):
        self.editable = not self.editable

        self.albumArtistEntry.set_editable(self.editable)
        self.albumTitleEntry.set_editable(self.editable)

        if self.editable == True:
            self.albumArtistEntry.set_css_classes(['album-artist-edit-mode'])
            self.albumTitleEntry.set_css_classes(['album-title-edit-mode'])
        else:
            self.albumArtistEntry.set_css_classes(['album-artist-play-mode'])
            self.albumTitleEntry.set_css_classes(['album-title-play-mode'])         
        
        if AlbumManager().album is not None and self.editable == False:
            #AlbumManager().album.is_compilation_album = self.compilationAlbumCheckButton.get_active()
            AlbumManager().album.apply_changes()
        
        self.refresh_list_box()    
    
    def fetch_cd_info(self, callback_event):
        self.status_label.set_label("Fetching CD Info From Internet...")

        musicbrainzngs.set_useragent("super-music-tools", "0.1", "musicbrainz_alias.language548@passmail.net")

        mb_id = ""

        try:
            result = musicbrainzngs.get_releases_by_discid(self.disc.id,
                                                           includes=["artists", "recordings", "isrcs"])
        except musicbrainzngs.ResponseError:
            self.status_label.set_label("CD Info Not Found Online")
            callback_event.set()
        else:
            print("RESPONSE")

            yaml_string = yaml.dump(result)
            print(yaml_string)
            if result.get("disc"):
                release_id = str(result["disc"]["release-list"][0]["id"])
                medium_count = result["disc"]["release-list"][0]["medium-count"]
                disc_number = 0
                disc_counter = 0
                for medium_entry in result["disc"]["release-list"][0]["medium-list"]:
                    if medium_entry["disc-list"][0]["id"] == self.disc.id:
                        print("Found disc number!")
                        disc_number = disc_counter
                    disc_counter = disc_counter + 1

                AlbumManager().album.artist = result["disc"]["release-list"][0]["artist-credit-phrase"]
                album_title = result["disc"]["release-list"][0]["title"]
                if disc_number > 0:
                    album_title = album_title + " (Disc " + str(disc_number + 1) + ")"                
                AlbumManager().album.title = album_title

                mb_id = result["disc"]["release-list"][0]["id"]

                try:
                    result = musicbrainzngs.get_release_by_id(mb_id,
                                                                   includes=["artists", "artist-credits", "recordings"])
                except musicbrainzngs.ResponseError:
                    self.status_label.set_label("CD Info Not Found Online")
                    callback_event.set()
 
                else:
                    print("RELEASE RELEASE RELEEASE")
                    yaml_string = yaml.dump(result)
                    print(yaml_string)
                    if result.get("release"):
                        populating_track_index = 0
                        for other in result["release"]["medium-list"][disc_number]["track-list"]:
                            track = AlbumManager().album.tracks[populating_track_index]
                            track.title = other["recording"]["title"]
                            artist_string = ""
                                                    
                            for track_artist in other["recording"]["artist-credit"]:
                                if type(track_artist) == str:#might say featuring so can concat here
                                    artist_string = artist_string + track_artist
                                else:
                                    artist_string = artist_string + track_artist["artist"]["name"]

                            track.artist = artist_string

                            populating_track_index = populating_track_index + 1

                        self.status_label.set_label("CD Info Retrieved Successfully")

                try:
                    image_data = musicbrainzngs.get_image_front(release_id)
                except musicbrainzngs.ResponseError:
                    self.status_label.set_label("Image data not found")
                else:
                    if image_data is not None:
                        m = magic.Magic(mime=True)
                        mime_type = m.from_buffer(image_data)

                        image_filename = ""

                        if mime_type == "image/jpeg":
                            image_filename = "./cache/cover.jpg"
                        elif mime_type == "image/gif":
                            image_filename = "./cache/cover.gif"
                        elif mime_type == "image/png":
                            image_filename = "./cache/cover.png"
            
                        if image_filename != "":
                            with open(image_filename, 'wb') as binary_file:
                                binary_file.write(image_data)
                        
                        AlbumManager().set_album_cover(image_filename)  
                        self.load_image(image_filename)
                callback_event.set()
 
            else:
                self.status_label.set_label("CD Info Not Found Online")
                callback_event.set()
                    
    def refresh_status_label(self):
        if self.album_source == "HDD":
            self.status_label.set_label("Playing From Library")
        else:
            self.status_label.set_label(AlbumManager().album.get_ripping_summary())

    
    def refresh_list_box(self):
        self.refresh_status_label()        

        self.albumArtistEntry.get_buffer().set_text(AlbumManager().album.artist, len(AlbumManager().album.artist))
        self.albumTitleEntry.get_buffer().set_text(AlbumManager().album.title, len(AlbumManager().album.title))

        if AlbumManager().album.current_playing_index != -1:
            self.tracks_list_selection.set_selected(AlbumManager().album.current_playing_index)
        
        AlbumManager().album.get_text_summary(self.paused, self.editable)
        

    def playFileClicked(self, button):
        self.open_dialog.open(self.main_window, None, self.play_file_select_callback)

    def open_image_clicked(self, button):
        if self.editable == True:
            self.open_dialog.open(self.main_window, None, self.image_select_callback)

    def clear_image(self):
        self.image_preview.clear()

    def image_select_callback(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            new_image_path = file.get_path()
            self.load_image(new_image_path)
        except GLib.Error as error:
            print(f"Error opening file: {error.message}")

    def load_image(self, new_image_path):
        print("LOAD IMAGE")
        self.imagePath = new_image_path
        self.image_preview.add_texture(self.imagePath)

    def albumTitleEntryChanged(self, entry):
        if AlbumManager().album is not None:
            AlbumManager().album.title = self.albumTitleEntry.get_buffer().get_text()
    
    def albumArtistEntryChanged(self, entry):
        if AlbumManager().album is not None:
            AlbumManager().album.artist = self.albumArtistEntry.get_buffer().get_text()

    def on_tracks_list_view_activate(self, user_data, activated_index):
        if not self.editable:
            if activated_index != AlbumManager().album.current_playing_index:
                AlbumManager().album.request_track_immediately(activated_index)
        
        

