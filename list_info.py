# Please read the accompanying license document and readme file
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject

class TextItem(GObject.Object):
    text = GObject.Property(type=str)

class TrackItem(GObject.Object):
    track_number = GObject.Property(type=int)
    artist = GObject.Property(type=str)
    title = GObject.Property(type=str)
    editable = GObject.Property(type=bool,default=False)
    playing = GObject.Property(type=bool,default=False)

def compare_track_items(item_a, item_b):
    result = True

    if item_a.track_number != item_b.track_number:
        return False

    if item_a.artist != item_b.artist:
        return False

    if item_a.title != item_b.title:
        return False

    if item_a.editable != item_b.editable:
        return False

    if item_a.playing != item_b.playing:
        return False

    
