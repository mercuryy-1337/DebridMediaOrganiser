# tmdb-tv-organiser
A Python script designed to organize unorganized TV show torrents by creating symbolic links in a structured format. The script utilizes The Movie Database (TMDb) API to fetch the proper TV show names and creates symlinks for episodes based on this information

# Features
- Fetches proper TV show names and years from TMDb.
- Supports resolution extraction and preservation (e.g., 720p, 1080p).
- Creates symlinks in a structured directory format (Show Name/Season xx/).
- Handles various naming conventions and unorganized torrent folders.

# Requirements
- Python 3.x
- pip package manager
- requests library

# Installation
1. Clone Repository:
``` sh
git clone https://github.com/mercuryy-1337/tmdb-tv-organiser.git
cd tmdb-tv-organiser
```
2. Install the required Python packages:
``` sh
pip install requests
pip install colorama
```
3. Get a TMDb API key:
- Sign up on [TMDb](https://www.themoviedb.org/)
- Go to your account settings and generate an API key then copy that key.

4. Run the script:
``` sh
python3 renameshows.py src_dir dest_dir
```

# Usage
**Basic Usage:**
```sh
python3 renameshows.py src_dir dest_dir
```
src_dir: Source directory containing the unorganized TV show files. <br/>
dest_dir: Destination directory where the symlinks will be created.

API Key Configuration:
On the first run, you will be prompted to enter your TMDb API key. The key will be saved in settings.json for future use.

## Example
**Source directory before running script:**
``` sh
src_dir/
├── Show.Name.S01E01.720p.mkv
├── Show.Name.S01E02.1080p.mkv
└── AnotherShow.S02E01.mkv
```
**Destination directory after running script:**
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

