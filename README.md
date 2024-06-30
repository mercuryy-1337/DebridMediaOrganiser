# tmdb-tv-organiser
A Python script designed to organize unorganized TV show torrents by creating symbolic links in a structured format. The script utilizes The Movie Database (TMDb) API to fetch the proper TV show names and creates symlinks for episodes based on this information

# Features
- Fetches proper TV show names and optionally IMDb IDs from TMDb.
- Supports resolution extraction and preservation (e.g., 720p, 1080p).
- Creates symlinks in a structured directory format (Show Name/Season xx/).
- Handles various naming conventions and unorganized torrent folders.
- Auto select tv show result (there will be bad matches and/or wrong grouping for shows with same names but different years)

# Requirements
- Python 3.x
- pip package manager
- requests library
- colorama library

# Installation
1. Clone Repository:
``` sh
git clone https://github.com/mercuryy-1337/tmdb-tv-organiser.git
cd tmdb-tv-organiser
```
2. Install the required Python packages:
``` sh
pip install requests colorama
```
3. Get a TMDb API key:
- Sign up on [TMDb](https://www.themoviedb.org/) if you don't already have an account.
- Once you've signed up or logged in, go to your account settings
- Head over to the API section then generate an API key.
- Once the key is generated, copy the first "API Key" and store this for later.

4. Run the script:
``` sh
python3 renameshows.py
```

# Usage
**Basic Usage:**
```sh
python3 renameshows.py [--force]
```
On the first run, the script will prompt you to enter the following settings, which will then be saved in settings.json for future use:
1. Your TMDb API key. Used to authenticate requests to The Movie Database (TMDb) API, enabling access to TV show data such as titles, IDs, and external identifiers like IMDb IDs. <br/>
2. Source directory containing the unorganized TV show files (src_dir). <br/>
3. Destination directory where the symlinks will be created and organised into (dest_dir). <br/>
4. Your preferred ID of choice for identifying TV shows, either 'tmdb' for TMDb (The Movie Database) or 'imdb' for IMDb (Internet Movie Database).

the optional --force flag enables the script to automatically select a result for TV show searches without requiring user input.


## Example
**Source directory before running script:**
``` sh
src_dir/
├── Show.Name.S01E01.720p.mkv
├── Show.Name.S01E02.1080p.mkv
└── AnotherShow.S02E01.mkv
```
**Destination directory after running script with no id parameter:**
``` sh
dest_dir/
├── Show Name (2020) {tmdb-0001}
│   ├── Season 1
│   │   ├── Show Name S01E01 720p.mkv -> ../../../../src_dir/Show.Name.S01E01.720p.mkv
│   │   └── Show Name S01E02 1080p.mkv -> ../../../../src_dir/Show.Name.S01E02.1080p.mkv
└── Another Show (2019) {tmdb-0002}
    ├── Season 2
    │   └── Another Show S02E01 720p.mkv -> ../../../../src_dir/AnotherShow.S02E01.mkv
```
**Destination directory after running script with imdb chosen for id:**
``` sh
dest_dir/
├── Show Name (2020) {imdb-tt1234567}
│   ├── Season 1
│   │   ├── Show Name S01E01 720p.mkv -> ../../../../src_dir/Show.Name.S01E01.720p.mkv
│   │   └── Show Name S01E02 1080p.mkv -> ../../../../src_dir/Show.Name.S01E02.1080p.mkv
└── Another Show (2019) {imdb-tt7654321}
    ├── Season 2
    │   └── Another Show S02E01 720p.mkv -> ../../../../src_dir/AnotherShow.S02E01.mkv
```

