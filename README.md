# debridshowrenamer
A Python script designed to organize unorganized TV show torrents by creating symbolic links in a structured format. The script utilizes The Movie Database (TMDb) API to fetch the proper TV show names and creates symlinks for episodes based on this information.
This script was mainly designed to work with a show folder in a zurg/rclone_rd mount but it can work with a folder that has a mix of both movies and shows.

# Features
- Fetches proper TV show names and optionally IMDb IDs from TMDb.
- Supports resolution extraction and preservation (e.g., 720p, 1080p).
- Creates symlinks in a structured directory format (Show Name/Season xx/).
- Handles various naming conventions and unorganized torrent folders.
- Auto select tv show result (there will be bad matches and/or wrong grouping for shows with same names but different years)
- Renames episodes according to plex's series naming convention (new feature)
- Stores created symlinks and checks existing symlinks before processing files
- filter out sample files
- Tries to match riven's naming scheme as much as possible

### Known issues/bugs
- The first show that's processed doesn't get queried through TMDB.
- ~~Multi-episode files are named according to the first episode in the file. e.g 'showname.s01e01e02.mkv' becomes 'showname - s01e01 - show_info {resolution}.mkv'~~ Now fixed.

### N.B
- This script is designed to work in a linux environment as Plex on windows doesn't resolve symlinks properly
- This script completeley disregards specials if they're not formatted like normal episodes e.g 'S00E01 - Special.mkv' will be renamed and organised but something like '{showname} - Special.mkv' will be skipped

# Requirements
- Python 3.x 
- pip package manager
- requests library
- colorama library

# Installation
1. Clone Repository:
``` sh
git clone -b riven https://github.com/mercuryy-1337/debridshowrenamer.git
cd debridshowrenamer
```
2. Install the required Python packages:
``` sh
pip install requests colorama
```
3. Install xmllint package if it doesn't exist
```sh
sudo apt install libxml2-utils
```
4. Get a TMDb API key:
- Sign up on [TMDb](https://www.themoviedb.org/) if you don't already have an account.
- Once you've signed up or logged in, go to your account settings
- Head over to the API section then generate an API key.
- Once the key is generated, copy the first "API Key" and store this for later.

5. Edit the plex_update.sh file with all the correct details

6. Run the script:
``` sh
python3 renameshows.py
```

# Usage
**Basic Usage:**
```sh
python3 renameshows.py [--simple]
```
On the first run, the script will prompt you to enter the following settings, which will then be saved in settings.json for future use:
1. Your TMDb API key. Used to authenticate requests to The Movie Database (TMDb) API, enabling access to TV show data such as titles, IDs and episode information. <br/>
2. Source directory containing the unorganized TV show files (src_dir). <br/>
3. Destination directory where the symlinks will be created and organised into (dest_dir), in this case it will be Riven's show directory path. <br/>

the optional --simple flag stops the script from querying individual episodes through TMDB and just renames the episodes into a simple format


## Example
**Source directory before running script:**
``` sh
src_dir/
├── Show.Name.S01E01.720p.mkv
├── Show.Name.S01E02.1080p.mkv
└── AnotherShow.S02E01.mkv
```
**Destination directory after running script**
``` sh
dest_dir/
├── Show Name (2020) {tmdb-0001}
│   ├── Season 1
│   │   ├── Show Name - S01E01 - show_info 720p.mkv -> ../../../../src_dir/Show.Name.S01E01.720p.mkv
│   │   └── Show Name - S01E02 - show_info 1080p.mkv -> ../../../../src_dir/Show.Name.S01E02.1080p.mkv
└── Another Show (2019) {tmdb-0002}
    ├── Season 2
    │   └── Another Show - S02E01-E02 720p.mkv -> ../../../../src_dir/AnotherShow.S02E01E02.mkv
```


