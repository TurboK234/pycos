# pycos
Python Converter Script for Recordings - Python script to automatically convert media files using FFmpeg with certain metadata/content awareness.

This script was written to automatically convert the recorded TV programs to a format that 1) is more compatible than the regular .ts files, 2) is more compact than the original broadcasted mpeg2 or h264 files and 3) is also able to include the DVB subtitle streams that are used at least in Finland. I also wanted to be able to save the EPG metadata to a format that can be used in an external media center program, in this case Kodi was the obvious and by far the best solution for me.

The script is based on my earlier project (BACAR), that was written for AutoHotkey. Although the script has been successfully converting my recordings for nearly four years, there has always been some fundamental issues with that script. The first and foremost is the fact that AutoHotkey is not (and will probably never be) platform independent, and it's possible that I won't have a Windows machine doing the conversion in the future. Secondly, since it was my first programming project ever, it has much to improve in logic and readability. This is not to say that pycos is perfect, but it's a huge improvement (platform-independent, better logic and readability, smaller file, separated configuration and rules from the main script).

Historically, the script was used in conjunction with Windows Media Center and .wtv files created by the program. Best results for metadata conversion were thought to be possible only with .wtv files, but it turned out that (at least) TVHeadend can record to .mkv files which include the metadata of the recording in a very similar manner as .wtv files. The actual conversion (without metadata scraping) works with all of the filetypes that are supported by FFmpeg.

The metadata file (.nfo (XML format), used by Kodi/XBMC) can be created even without proper metadata (TS-files, for example, the .nfo can be set to store the filename and the recording date), and it can be edited manually if the metadata is present in some other format. No external scraping (meaning that the metadata would be retrieved either from a backend specific database or from a online source) is included and it's not a planned TO-DO, although technically possible. This will be easiest to implement (by someone) when a specific PVR backend is already in use.

The meaning of the rules.txt file can seem confusing. To clarify, there are two reasons to use the rules:
1) Include or exclude specific streams from the source file. As an example, I don't want to include the hearing impaired audio, so I have a rule to exclude those streams (hearing impaired streams are, for some reason, marked as Dutch language (dut) here in Finland). On the other hand, I want to include subtitle streams on those channels that provide DVB subtitles. I have rules for those channels and streams also.
2) Create a .nfo file that has the proper headers and information included. This is recording backend dependent, and output is entirely dependent of the media center program (Kodi). All of the programs are labeled as "movie", to avoid super-complex setup and results.

To view the metadata in Kodi/XBMC you have to select "Local metadata only" (.nfo icon) when adding the folder to your library. Frequent/daily library updates with XBMC Library Auto Update (Plugin) are recommended.

Basic knowledge of FFmpeg and conversion parameters are required for proper setup. One needs to investigate the source files with FFprobe to define the rules for the wanted streams and/or metadata headers, this is the most time consuming part of the setup.

## Requirements:
* Python 3.7 or higher
* FFmpeg installed (can also be a portable installation, ffmpeg directory can be specified)
* At least 10 gigabytes of free space on the target drive
* Windows or GNU/Linux compatible. Should probably work with OSX, untested

## Usage:
* Download the repository either manually as .zip (and unpack) or with git (>git clone https://github.com/TurboK234/pycos).
* Copy the pycos.py file if needed (to a "scripts" folder), this is optional.
* Copy the settings.txt and rules.txt (either from the root folder or from the defaults folder (identical files)) to a desired place (e.g. ~/pycos_settings/setting1/ ) and rename the settings file to something else if you want. NOTE: You can also run the script in the original folder and use the settings.txt and rules.txt in the same folder by default, but this is the least flexible way, and it's difficult to have several conversion "profiles" this way.
* Edit the settings file. Do this carefully. And read the comments that should give enough information to get you started.
* Edit the rules.txt (NOTE: rules.txt can not be renamed, but it can reside in a different folder than settings, if specified in the settings file). It is mandatory to study the files with FFprobe in order to create rules, but the rules are optional if you don't need to specify the streams to be mapped or you don't want to create .nfo files.
* Run the program with Python. The syntax is >python path/to/pycos.py path/to/settingsfile . You can also just run >python /path/to/pycos.py , but then you need to have properly set settings.txt (with the original name) in the same folder as pycos.py .
