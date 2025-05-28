# Please read the accompanying license document and readme file
import time

import sys
import os
import gi
import subprocess
import threading
import shutil
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import yaml
from cdgui import CDGui
from gi.repository import Graphene
from album_manager import AlbumManager
from mpris_server.adapters import MprisAdapter
from mpris_server.events import EventAdapter
from mpris_server.server import Server
from mpris_server.mpris.metadata import Metadata, MetadataEntries, update_metadata
import fcntl
import struct
import pyudev
import threading
from mpris_server import Track, PlayState, Position

CDROM_DRIVE_STATUS = 0x5326  # ioctl command for drive status
CDS_NO_DISC = 2  # Status code meaning no disc

def is_cd_in_drive(device="/dev/sr0"):
    try:
        with open(device, 'rb') as cdrom:
            status = fcntl.ioctl(cdrom, CDROM_DRIVE_STATUS, struct.pack("I", 0))
            return status != CDS_NO_DISC
    except Exception as e:
        print(f"Error checking drive {device}: {e}")
        return False

class MyAppAdapter(MprisAdapter):
    def __init__(self, play_pause, play, stop, next_func, previous):
        super().__init__("Hello World")
        self.play_pause_fn = play_pause
        self.play_fn = play
        self.stop_fn = stop
        self.next_func_fn = next_func
        self.previous_func_fn = previous
    
    def pause(self):
        print("pause")
        self.play_pause_fn()
        print("pause done")

    def play(self):
        print("PLAY")
        self.play_fn()

    def previous(self):
        self.previous_func_fn()

    def resume(self):
        print("RESUME")
        self.play_pause_fn()

    def stop(self):
        self.stop_fn()

    
    def metadata(self) -> Metadata:
        metadata = Metadata()

        if AlbumManager().album is not None:
            metadata[MetadataEntries.ALBUM] = AlbumManager().album.title
            metadata[MetadataEntries.ALBUM_ARTISTS] = [AlbumManager().album.artist]
            metadata[MetadataEntries.ART_URL] = ""
            metadata[MetadataEntries.ARTISTS] = [AlbumManager().album.get_current_track_artist()]
            metadata[MetadataEntries.AS_TEXT] = ""
            metadata[MetadataEntries.AUDIO_BPM] = ""
            metadata[MetadataEntries.AUTO_RATING] = ""
            metadata[MetadataEntries.COMMENT] = ""
            metadata[MetadataEntries.COMPOSER] = ""
            metadata[MetadataEntries.CONTENT_CREATED] = ""
            metadata[MetadataEntries.DISC_NUMBER] = ""
            metadata[MetadataEntries.FIRST_USED] = ""
            metadata[MetadataEntries.GENRE] = ""
            metadata[MetadataEntries.LAST_USED] = ""
            metadata[MetadataEntries.LENGTH] = ""
            metadata[MetadataEntries.LYRICIST] = ""
            metadata[MetadataEntries.TITLE] = AlbumManager().album.get_current_track_title()
            metadata[MetadataEntries.TRACK_ID] = ""
            metadata[MetadataEntries.TRACK_NUMBER] = ""
            metadata[MetadataEntries.URL] = ""
            metadata[MetadataEntries.USE_COUNT] = ""
            metadata[MetadataEntries.USER_RATING] = ""
        else:
            metadata[MetadataEntries.TITLE] = "test"
        

        return metadata

    def get_playstate(self) -> PlayState:
        if AlbumManager().album is None:
            return PlayState.STOPPED
        elif AlbumManager().album.get_paused() == True:
            return PlayState.PAUSED
        else:
            return PlayState.PLAYING
        
    def on_playpause(self, playing):
        print("Do play pause")
        self.play_pause()
        print("Done play pause")
        
    def on_play(self, playing):
        self.play()
        
    def on_stop(self):
        self.stop()
        
    def on_previous(self):
        self.previous()
        
    def on_next(self):
        self.next_func()
	
    def get_current_position(self) -> Position:
        return 0

    def can_control(self) -> bool:
        return True

    def can_go_next(self) -> bool:
        return True

    def can_go_previous(self) -> bool:
        return True

    def can_pause(self) -> bool:
        print("can_pause?")
        return self.get_playstate() == PlayState.PLAYING or self.get_playstate() == PlayState.PAUSED

    def can_play(self) -> bool:
        print("can_play?")
        return self.get_playstate() == PlayState.PAUSED or self.get_playstate() == PlayState.STOPPED

    def can_seek(self) -> bool:
        print("can_seek?")
        return False

    def get_next_track(self) -> Track:
        return AlbumManager().album.get_next_track_data()

    def get_previous_track(self) -> Track:
        return AlbumManager().album.get_previous_track_data()

    def get_shuffle(self) -> bool:
        pass

    def get_stream_title(self) -> str:
        pass

    def is_mute(self) -> bool:
        return False

    def is_playlist(self) -> bool:
        return False

    def is_repeating(self) -> bool:
        return False

    def next(self):
        self.next_func_fn()

    def open_uri(self, uri: str):
        pass

      
    def set_mute(self, value: bool):
        pass

    def set_repeating(self, value: bool):
        pass

    def set_shuffle(self, value: bool):
        pass

class MyAppEventHandler(EventAdapter):
    def on_playback(self):
        super().on_playback()
    
    def on_playpause(self):
        super().on_playpause()

class MainWindow(Gtk.ApplicationWindow):
    rip_locked = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
.album-title-play-mode {
    background-color: transparent;
    color: #FFFFFF;
    border: 0px;
    font-size: 20px
}

.album-title-edit-mode {
    background-color: #f0f0f0;
    color: #000000;
    font-size: 20px
}

.track-title-play-mode {
    background-color: transparent;
    color: #FFFFFF;
    border: 0px;
    font-size: 16px
}

.track-title-play-mode-playing {
    background-color: transparent;
    color: #0000FF;
    border: 0px;
    font-size: 16px
}

.track-title-edit-mode {
    background-color: #f0f0f0;
    color: #000000;
    font-size: 16px
}

.album-artist-play-mode {
    background-color: transparent;
    color: #FFFFFF;
    border: 0px;
    font-size: 10px
}

.album-artist-edit-mode {
    background-color: #f0f0f0;  /* Light grey background */
    color: #000000;
    font-size: 10px
}

.track-artist-play-mode {
    background-color: transparent;
    color: #FFFFFF;
    border: 0px;
    font-size: 10px
}

.track-artist-play-mode-playing {
    background-color: transparent;
    color: #0000FF;
    border: 0px;
    font-size: 10px
}

.track-artist-edit-mode {
    background-color: #f0f0f0;  /* Light grey background */
    color: #000000;
    font-size: 10px
}

.image-button {
    padding: 0px;
    background-color: transparent;
    border-width: 0;
}

.transport-button-large {
    padding: 0px;
    background-color: transparent;
    border-width: 0;
    color: #FFFFFF;
    font-size: 40px
}

.transport-button-small {
    padding: 0px;
    background-color: transparent;
    border-width: 0;
    color: #FFFFFF;
    font-size: 20px
}

.list-item {
    padding: 0px;
    background-color: transparent;
    border-width: 0;
}

button {
    padding: 0px;
    background-color: transparent;
    border-width: 0;
    color: #FFFFFF;
    font-size: 20px
}

listview {
    background-color: transparent;
}

row {
    background-color: #000000;
}

window {
    background-color: black;
}

.status-label {
    background-color: transparent;
    color: #FFFFFF;
    border: 0px;
    font-size: 10px
}

""")

        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        AlbumManager().load_config()
        
        self.set_default_size(380, 640)
        self.set_title("Super Music Tools")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_margin_top(5)
        box.set_margin_start(5)
        box.set_margin_end(5)
        box.set_margin_bottom(5)

        top_controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        top_controls_box.set_margin_top(5)
        top_controls_box.set_margin_start(5)
        top_controls_box.set_margin_end(5)
        top_controls_box.set_margin_bottom(5)
        top_controls_box.set_homogeneous(True)

        box.append(top_controls_box)

        self.open_folder_button = Gtk.Button(label="Folder")
        self.open_folder_button.connect('clicked', self.open_folder_clicked)
        top_controls_box.append(self.open_folder_button)

        self.open_cd_button = Gtk.Button(label="CD")
        self.open_cd_button.connect('clicked', self.open_cd_clicked)
        top_controls_box.append(self.open_cd_button)

        self.edit_mode_button = Gtk.Button(label="Edit")
        self.edit_mode_button.connect('clicked', self.toggle_edit_mode)
        top_controls_box.append(self.edit_mode_button)
        
        self.cd_gui = CDGui(self)
        AlbumManager().add_album_clear_callback(self.cd_gui.refresh_list_box)
        AlbumManager().add_album_rip_complete_callback(self.on_album_rip_complete)
        AlbumManager().add_album_data_change_callback(self.on_album_data_change)
        AlbumManager().add_cd_fetch_complete_callback(self.on_cd_fetch_complete)
                
        box.append(self.cd_gui.box1)
          
        self.set_child(box)

        my_adapter = MyAppAdapter(self.cd_gui.pause_or_resume, self.cd_gui.do_play, self.cd_gui.do_stop, self.cd_gui.do_next, self.cd_gui.do_previous)
        mpris = Server('MyApp', adapter=my_adapter)

        self.mpris = mpris
        self.mpris_event_handler = MyAppEventHandler(root=mpris.root, player=mpris.player)
        
        self.mpris_thread = threading.Thread(target=mpris.loop)
        self.mpris_thread.start()

        self.open_dialog = Gtk.FileDialog.new()
        self.open_dialog.set_initial_folder(Gio.File.new_for_path(AlbumManager().music_dir))
        self.open_dialog.set_title("Select")
        
    def open_folder_clicked(self, button):
        self.open_dialog.select_folder(self, None, self.folder_select_callback)

    def open_cd_clicked(self, button):
        self.load_cd()

    def folder_select_callback(self, dialog, result):
        try:
            if AlbumManager().album is not None:
                if AlbumManager().album.get_play_lock() == True:
                    self.cd_gui.do_stop()
            file = dialog.select_folder_finish(result)
            has_image = AlbumManager().populate_from_folder(file.get_path())
            print("HAS IMAGE = " + str(has_image))
            if has_image == True:
                self.cd_gui.load_image(AlbumManager().cache_dir + "/temp.png")
            self.cd_gui.album_source = "FOLDER"
            self.cd_gui.playback_mode = "FILE"     
            self.cd_gui.refresh_list_box()
        except GLib.Error as error:
            print(f"Error opening file: {error.message}")
    
    def load_cd(self):
        print("Load CD, rip locked? " + str(self.rip_locked))
        if self.rip_locked == False:
            self.rip_locked = True
            self.open_cd_button.set_sensitive(False)
            self.edit_mode_button.set_sensitive(False)
            self.open_folder_button.set_sensitive(False)
            AlbumManager().clean_up()
            self.cd_gui.reset()
            callback_event = threading.Event()
            self.cd_gui.load_cd(callback_event)
            

    def on_album_rip_complete(self):
        print("Rip Complete")
        self.rip_locked = False
        self.open_cd_button.set_sensitive(True)
        self.open_folder_button.set_sensitive(True)
        #self.cd_gui.refresh_status_label()

    def on_cd_fetch_complete(self):
        self.edit_mode_button.set_sensitive(True)

    def on_album_data_change(self):
        self.cd_gui.refresh_list_box()

    def toggle_edit_mode(self, button):
        self.cd_gui.toggle_edit_mode()
    
class MyApp(Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        try:
            import pyi_splash
            pyi_splash.update_text("UI Loaded ...")
            pyi_splash.close()
        except:
            pass
        self.connect('activate', self.on_activate)
        self.connect('shutdown', self.on_destroy)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()
    
    def on_destroy(self, app):
        self.win.mpris.quit_loop()
        self.win.mpris_thread.join()
        AlbumManager().clean_up()

app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)

