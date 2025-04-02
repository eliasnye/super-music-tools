# Please read the accompanying license document and readme file
from musicmodels import TrackProperties
from musicmodels import AlbumProperties
import os
import yaml
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject
from list_info import TextItem, TrackItem

# AlbumManager is a Python Singleton which handles various 
# events/communications etc for the current album.
# TODO: This should be replaced with somethinig more like a
# "proper" event system.
class AlbumManager:
    _instance = None
    album = None
    music_dir = os.path.expanduser("~/Music") + "/"
    on_track_complete_callbacks = []
    on_image_update_callbacks = []
    on_album_clear_callbacks = []
    on_album_rip_complete_callbacks = []
    on_album_data_change_callbacks = []
    on_cd_fetch_complete_callbacks = []
    list_model = None
    

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlbumManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    # Load a new album from a folder (must be .flac files)
    def populate_from_folder(self, folder):
        self.album = AlbumProperties(self.list_model)
        self.album.album_manager = self
        return self.album.populate_from_folder(folder)

    # Load album from CD in drive
    def populate_tracks_to_rip(self, num_tracks, fetch_cd_info, callback_event):
        self.album = AlbumProperties(self.list_model)
        self.album.album_manager = self
        self.album.populate_tracks_to_rip(num_tracks, fetch_cd_info, callback_event)
    
    # Set the album's front cover image - this will eventually
    # line-up the relevant changes to flac metadata
    def set_album_cover(self, image_path):
        self.album.set_album_cover(image_path)
    

    # Below is the current callback mechanism,
    # this should be replaced
    def add_track_complete_callback(self, callback):
        self.on_track_complete_callbacks.append(callback)        

    def add_image_update_callback(self, callback):
        self.on_image_update_callbacks.append(callback)

    def add_album_clear_callback(self, callback):
        self.on_album_clear_callbacks.append(callback)

    def add_album_rip_complete_callback(self, callback):
        self.on_album_rip_complete_callbacks.append(callback)

    def add_album_data_change_callback(self, callback):
        self.on_album_data_change_callbacks.append(callback)

    def add_cd_fetch_complete_callback(self, callback):
        self.on_cd_fetch_complete_callbacks.append(callback)

    def on_cd_fetch_complete(self):
        print("AM FETCH COMP")

        for callback in self.on_cd_fetch_complete_callbacks:
            callback()

    def on_track_complete(self):
        self.album.on_track_complete()
        for callback in self.on_track_complete_callbacks:
            callback()
    
    def on_album_rip_complete(self):
        for callback in self.on_album_rip_complete_callbacks:
            callback()

    def on_album_data_change(self):
        for callback in self.on_album_data_change_callbacks:
            callback()
    
    def clean_up(self):    
        if self.album is not None:
            self.album.clean_up()
            self.list_model.remove_all()
            for callback in self.on_album_clear_callbacks:
                callback()       

    # Load configs and establish central list model for track list data
    def load_config(self):
        self.list_model = Gio.ListStore(item_type=TrackItem)
        if os.path.exists('config.yml'):
            with open('config.yml', 'r') as file:
                user_prefs = yaml.safe_load(file)
                self.music_dir = user_prefs['config']['music_dir']
                if self.music_dir.endswith("/") == False:
                    self.music_dir = self.music_dir + "/"

