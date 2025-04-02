# super-music-tools

Please note that this app is in pre-alpha! Use as a dev for testing!

## About Super Music Tools

Super Music Tools is a small app designed to streamline the process of CD ripping and tagging to files in FLAC format.

## Binary Downloads

These are currently on Proton Drive:

x86_64: https://drive.proton.me/urls/HHRC6H40EG#31HMrWMJ1OOv
x86_64 sha256: 50b2eafa69bc7f104b5bb8fb992200d99090dda8b96e982311a82aef7855b993

arm64: https://drive.proton.me/urls/1HNW3WR9Q4#v3l1RivlOPmr
arm64 sha256: b84fb2ed0d3e1a5810f1797ff2a4d7f02b5bf7aacb95c1036f323e75adeca463

Install the following before running the binary:

ffmpeg
sox
cdparanoia

## Key Features:

Immediately start listening to a CD and rip it in the background - after listening, it's then in the library folder on your device.

Edit metadata tags while listening - useful especially when the CD information can't be retrieved online.

## How it works

This app is written in Python and executes ffmpeg, cdparanoia and sox as subprocesses in parallel. I owe a heavy debt to the various authors of the abcde CD ripper whose code I spent a lot of time studying. This project was originally a hack of abcde that played the CD during the rip.

When the app loads a new CD in the drive, it immediately starts running CD Paranoia to rip each track in succession to a WAV file. WAV files don't need to be complete to start playback using sox, so once a certain amount of data is present in the file, the app will call sox to run any outstanding playback request. In practical terms this means that you pretty much get a similar experience to using a CD player, including being able to skip tracks, with a small and tolerable buffering time, especially if you're using a fast drive. The app uses an asynchronous catch-up mechanism to apply pending changes in tags etc. And encode the file to FLAC using ffmpeg. Usually, part way through the first listen of the album, it will already be ripped.

Part of the main purpose of this app for me is being able to quickly type in an album artist and title during the rip if the album is not in the online database. This is particularly useful when buying CDs at shows by small local bands. The album won't be fully tagged, but it is roughly titled in the right folder and additional tags can then be added at leisure during playback. This makes the whole process of manually ripping and tagging obscure CDs much more painless.

By default, music will be ripped to your Music folder in home. Please note that this app is in pre alpha and will quite happily over write existing files. If you want to use a different music folder you just need to add a config.yml file to the same folder as the app, and specify your folder like this:

config:
    music_dir: "/media/my_username/Music/"

Albums are always put into a parent folder with the same name as the album artist, then a sub folder with the album title. Rips are always done as FLAC. There will be more options and formats for this supported in future. Likewise if you choose to open a folder, that folder can be anywhere but must contain FLAC files.

Please note, at the moment it overwrites existing flac files without hesitation!

## Running from source/Building

You must use Python 3.12 - create a Python 3.12 Virtual env and pip[ install:

pyyaml
pycairo
pydbus
discid
python-libdiscid
musicbrainzngs
mutagen
pillow
opencv-python
dbus-python
PyGObject - must be pegged at 3.50.0
mpris_server
pathvalidate
pyudev

On furios this required me to install using apt:

gcc
libcairo2-dev
python-is-python3
setuptools-python3
python3-dev
libgirepository1.0-dev
autoconf
libtool
libdbus-glib-1-dev
ffmpeg
sox

After that it's just python3.12 main.py with your virtual environment activated.

You can build the app using pyinstaller.

After the standard build you need to copy the contents of emoji/unicode_codes from your Python Lib to _internal/emoji/unicode_codes
You also need to ensure that there is a folder called "cache" at the same level as your main executable.



