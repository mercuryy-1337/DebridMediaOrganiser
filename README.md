# DebridMediaOrganiser
A Python script designed to organize unorganized media torrents (movies and shows) by creating symbolic links in a structured format. The script utilizes the cinemeta API to fetch the proper TV and movie details then creates symlinks based on this information. It also utilizes The Movie Database API to check which shows are anime so they can be moved to a seperate folder if the user chooses to do so.
Originally, this script was designed to work with a show folder in a zurg/rclone_rd mount but it can now work with a folder that has a mix of both movies and shows as it will sort everything accordingly

# Features
- Fetches proper TV show and movie details such as the proper name, imdb id and release year
- Supports resolution extraction and preservation (e.g., 720p, 1080p).
- Creates symlinks in a structured directory format (Show Name (yeaar) {imdb-tt123456789}/Season xx/).
- Handles various naming conventions and unorganized torrent folders.
- Renames and organises media according to plex's naming convention
- Stores created symlinks and checks existing symlinks before processing files
- filter out sample files
- Matches riven's naming scheme

### Known issues/bugs
- ~~The first show that's processed doesn't get queried through TMDB.~~
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
git clone -b riven https://github.com/mercuryy-1337/DebridMediaOrganiser.git
cd DebridMediaOrganiser
```
2. Install the required Python packages:
``` sh
pip install requests colorama
```
3. Install xmllint package if it doesn't exist
```sh
sudo apt install libxml2-utils
```
4. Get a TMDb API key (optional, only if you want anime shows to have their own directory):
- Sign up on [TMDb](https://www.themoviedb.org/) if you don't already have an account.
- Once you've signed up or logged in, go to your account settings
- Head over to the API section then generate an API key.
- Once the key is generated, copy the first "API Key" and store this for later.

~~5. Edit the plex_update.sh file with all the correct details~~

6. Run the script:
``` sh
python3 organisemedia.py
```

# Usage
**Basic Usage:**
```sh
python3 organisemedia.py [--split-dirs]
```
On the first run, the script will prompt you to enter the following settings, which will then be saved in settings.json for future use:
1. Your TMDb API key (if you run the script with the `--split-dirs` flag. It is used to authenticate requests to The Movie Database (TMDb) API, enabling access to TV show data such as keywords associated with the show. <br/>
2. Source directory containing the unorganized torrent files (src_dir) e.g `/mnt/zurg/__all__`. <br/>
3. Destination directory where the symlinks will be created and organised into (dest_dir), in this case it will be Riven's top most directory path e.g `/mnt/riven`. <br/>

the optional --split-dirs flag allows the script to place anime shows in it's own folder, separate from the default shows folder.


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
├── shows
│   ├── Show Name (2020) {imdb-tt123456789}
│   │   ├── season 01
│   │   │   ├── Show Name (2020) - s01e01 - show_info 720p.mkv -> ../../../../src_dir/Show.Name.S01E01.720p.mkv
│   │   │   └── Show Name (2020) - s01e02 - show_info 1080p.mkv -> ../../../../src_dir/Show.Name.S01E02.1080p.mkv
│   └── Another Show (2019) {imdb-tt987654321}
│       ├── season 02
│       │   └── Another Show (2019) - s02e01-e02 720p.mkv -> ../../../../src_dir/AnotherShow.S02E01E02.mkv
└── movies
    ├── Movie Title (2021) {imdb-tt1122334455}
    │   └── Movie Title (2021) {imdb-tt1122334455}.mkv -> ../../../../src_dir/Movie.Title.2021.720p.mkv
    └── Another Movie (2018) {imdb-tt9988776655}
        └── Another Movie (2018) {imdb-tt9988776655}.mkv -> ../../../../src_dir/Another.Movie.2018.1080p.mkv
```
**Destination directory after running script with --split-dirs flag**
```
dest_dir/
├── shows
│   ├── Show Name (2020) {imdb-tt123456789}
│   │   ├── season 01
│   │   │   ├── Show Name (2020) - s01e01 - show_info 720p.mkv -> ../../../../src_dir/Show.Name.S01E01.720p.mkv
│   │   │   └── Show Name (2020) - s01e02 - show_info 1080p.mkv -> ../../../../src_dir/Show.Name.S01E02.1080p.mkv
│   └── Another Show (2019) {imdb-tt987654321}
│       ├── season 02
│       │   └── Another Show (2019) - s02e01-e02 720p.mkv -> ../../../../src_dir/AnotherShow.S02E01E02.mkv
├── anime_shows
│   ├── Anime Show (2021) {imdb-tt1122334455}
│   │   ├── season 01
│   │   │   ├── Anime Show (2021) - s01e01 - anime_info 720p.mkv -> ../../../../src_dir/Anime.Show.S01E01.720p.mkv
│   │   │   └── Anime Show (2021) - s01e02 - anime_info 1080p.mkv -> ../../../../src_dir/Anime.Show.S01E02.1080p.mkv
│   └── Another Anime (2018) {imdb-tt9988776655}
│       ├── season 02
│       │   └── Another Anime (2018) - s02e01-e02 720p.mkv -> ../../../../src_dir/Another.Anime.S02E01E02.mkv
└── movies
    ├── Movie Title (2021) {imdb-tt5566778899}
    │   └── Movie Title (2021) {imdb-tt5566778899}.mkv -> ../../../../src_dir/Movie.Title.2021.720p.mkv
    └── Another Movie (2018) {imdb-tt9988776655}
        └── Another Movie (2018) {imdb-tt9988776655}.mkv -> ../../../../src_dir/Another.Movie.2018.1080p.mkv
```


