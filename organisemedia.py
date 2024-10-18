import os
import argparse
import re, string
import shutil
import requests
import json
import time
import difflib
import pickle, subprocess
from collections import defaultdict
import asyncio, aioconsole, aiohttp
from colorama import init, Fore, Style

init(autoreset=True)


SETTINGS_FILE = 'settings.json'
links_pkl = 'symlinks.pkl'
ignored_file = 'ignored.pkl'
_api_cache = {}
season_cache = {}

LOG_LEVELS = {
    "[SUCCESS]": {"level": 10, "color": Fore.LIGHTGREEN_EX},
    "[INFO]": {"level": 20, "color": Fore.LIGHTBLUE_EX},
    "ERROR": {"level": 30, "color": Fore.RED},
    "[WARN]": {"level": 40, "color": Fore.YELLOW},
    "[DEBUG]": {"level": 50, "color": Fore.LIGHTMAGENTA_EX}
}

print_lock = asyncio.Lock()
input_lock = asyncio.Lock()


def log_message(log_level, message):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    if log_level in LOG_LEVELS:
        log_info = LOG_LEVELS[log_level]
        formatted_message = f"{Fore.WHITE}{current_time} | {log_info['color']}{log_level} {Fore.WHITE}| {log_info['color']}{message}"
        colored_message = f"{log_info['color']}{formatted_message}{Style.RESET_ALL}"
        print(colored_message)
    else:
        print(f"Unknown log level: {log_level}")

def are_similar(folder_name, show_name, threshold=0.8):
    """Check if the folder name is mostly the same as the show name"""
    folder_name = re.sub(r'[^\w\s]', '', folder_name)
    show_name = re.sub(r'[^\w\s]', '', show_name)
    similarity = difflib.SequenceMatcher(None, folder_name, show_name).ratio()
    #log_message('DEBUG', f"Name 1: {folder_name}, Name 2: {show_name}, Similarity = {similarity >= threshold}")
    return similarity >= threshold


def save_link(data, file_path):
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

def load_links(file_path):
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return set()
    
def save_ignored(ignored_files):
    with open(ignored_file, 'wb') as f:
        pickle.dump(ignored_files, f)

def load_ignored():
    if os.path.exists(ignored_file):
        with open(ignored_file, 'rb') as f:
            return pickle.load(f)
    return set()

def save_settings(api_key, src_dir, dest_dir):
    settings = {
        'api_key': api_key,
        'src_dir': src_dir,
        'dest_dir': dest_dir,
    }
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file, indent=4)

def get_api_key():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            settings = json.load(file)
            if settings['api_key']:
                return settings.get('api_key')
            else:
                return None
    return None

def prompt_for_api_key():
    api_key = input("Please enter your TMDb API key: ")
    
    try:
        with open(SETTINGS_FILE, 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        settings = {}
    
    settings['api_key'] = api_key
    
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file, indent=4)

def prompt_for_settings(api_key):
    src_dir = input("Enter the source directory path: ")
    dest_dir = input("Enter the destination directory path: ")
    save_settings(api_key, src_dir, dest_dir)
    return src_dir, dest_dir

def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            return json.load(file)
    return {}


def get_moviedb_id(imdbid):
    url = f"https://v3-cinemeta.strem.io/meta/series/{imdbid}.json"
    try:
        response = requests.get(url)
        try:
            movie_data = response.json()
        except requests.exceptions.RequestException as e:
            log_message('ERROR', f"Error: {e}")
            return None
        
        if "meta" in movie_data and movie_data['meta']:
            movie_info = movie_data.get('meta')
            
            if 'moviedb_id' in movie_info:
                return movie_info['moviedb_id']
            else:
                log_message('[WARN]',f"moviedb_id {imdbid}not found in movie_info")
                return None
        else:
            return None
    except requests.exceptions.RequestException as e:
        log_message('ERROR', f"Error: {e}")

def is_anime(moviedb_id):
    api_key = get_api_key()
    if moviedb_id is None:
        return False

    url = f"https://api.themoviedb.org/3/tv/{moviedb_id}/keywords"
    params = {'api_key': api_key}

    try:
        with requests.Session() as session:
            response = session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            keywords = data.get('results', [])
            return any(keyword.get('name') == "anime" for keyword in keywords)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return False
    
async def get_movie_info(title, year=None, force=False):
    global _api_cache
    formatted_title = title.replace(" ", "%20")
    cache_key = f"movie_{formatted_title}_{year}"
    
    if cache_key in _api_cache:
        return _api_cache[cache_key]
    
    url = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={formatted_title}.json"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                async with print_lock:
                    if response.status == 404:
                        imdb_id = await aioconsole.ainput(f"{Fore.YELLOW}Movie '{title}' not found. {Fore.WHITE}Please enter the IMDb ID: ")
                        if imdb_id:
                            url = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={imdb_id}.json"
                            async with session.get(url) as response:
                                pass
                        else:
                            log_message('[WARN]', "IMDB id not provided, returning default title and dir")
                            return title

                    if response.status != 200:
                        log_message('ERROR', f"Error fetching movie information: HTTP {response.status}")
                        return title
                try:
                    movie_data = await response.json()
                except aiohttp.ContentTypeError:
                    log_message('ERROR', "Error decoding JSON response")
                    return None

                if 'metas' in movie_data and movie_data['metas']:
                    movie_options = movie_data['metas']
                    matched = False
                    for movie_info in movie_options:
                        imdb_id = movie_info.get('imdb_id')
                        movie_title = movie_info.get('name')
                        year_info = movie_info.get('releaseInfo')
                        
                        if are_similar(title.lower().strip(), movie_title.lower(), 0.90):
                            proper_name = f"{movie_title} ({year_info}) {{imdb-{imdb_id}}}"
                            _api_cache[cache_key] = proper_name
                            return proper_name
                    if force:
                        
                        chosen_movie = movie_options[0]
                        imdb_id = chosen_movie.get('imdb_id')
                        movie_title = chosen_movie.get('name')
                        year_info = chosen_movie.get('releaseInfo')
                        proper_name = f"{movie_title} ({year_info}) {{imdb-{imdb_id}}}"
                        return proper_name
                    if not matched:
                        async with print_lock:
                            log_message('[WARN]', f"No exact match found for {title}. Please choose from the following options or enter IMDb ID directly:")
                            for i, movie_info in enumerate(movie_options[:3]):
                                imdb_id = movie_info.get('imdb_id')
                                movie_title = movie_info.get('name')
                                year_info = movie_info.get('releaseInfo')
                                log_message('[INFO]', f"{i+1}. {movie_title} ({year_info})")
                            choice = await aioconsole.ainput("Enter the number of your choice, or enter IMDb ID directly: ")
                            if choice.lower().startswith('tt'):
                                imdb_id = choice
                                url = f"https://cinemeta-live.strem.io/meta/movie/{imdb_id}.json"
                                async with session.get(url) as response:
                                    if response.status == 200:
                                        movie_data = await response.json()
                                        if 'meta' in movie_data and movie_data['meta']:
                                            movie_info = movie_data['meta']
                                            imdb_id = movie_info.get('imdb_id')
                                            movie_title = movie_info.get('name')
                                            year_info = movie_info.get('releaseInfo')
                                            proper_name = f"{movie_title} ({year_info}) {{imdb-{imdb_id}}}"
                                            _api_cache[cache_key] = proper_name
                                            return proper_name
                                        else:
                                            log_message('ERROR', "No movie found with the provided IMDb ID")
                                            return title
                                    else:
                                        log_message('ERROR', "Error fetching movie information with IMDb ID")
                                        return title
                            else:
                                try:
                                    choice = int(choice) - 1
                                    if 0 <= choice < len(movie_options[:3]):
                                        chosen_movie = movie_options[choice]
                                        imdb_id = chosen_movie.get('imdb_id')
                                        movie_title = chosen_movie.get('name')
                                        year_info = chosen_movie.get('releaseInfo')
                                        proper_name = f"{movie_title} ({year_info}) {{imdb-{imdb_id}}}"
                                        return proper_name
                                    else:
                                        log_message('[WARN]', f"Invalid choice, returning '{title}'")
                                        return title
                                except ValueError:
                                    log_message('[WARN]', f"Invalid input, returning '{title}'")
                                    return title
        except aiohttp.ClientError as e:
            log_message('ERROR', f"Error fetching movie information: {e}")
            return f'{title} {year}'


async def get_series_info(series_name, year=None, split=False, force=False):
    global _api_cache
    log_message("[INFO]", f"Current file: {series_name} year: {year}")
    shows_dir = "shows"
    series_name = series_name.rstrip(string.punctuation)
    formatted_name = series_name.replace(" ", "%20")
    cache_key = f"series_{formatted_name}_{year}"
    if cache_key in _api_cache:
        return _api_cache[cache_key]
    
    search_url = f"https://v3-cinemeta.strem.io/catalog/series/top/search={formatted_name}.json"
    response = requests.get(search_url, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Error searching for series: {response.status_code}")
    
    search_results = response.json()
    metas = search_results.get('metas', [])
    
    selected_index = 0
    if not metas:
        return series_name, None, shows_dir
    
    if force:
        if year:
            for i, meta in enumerate(metas):
                release_info = meta.get('releaseInfo')
                release_info = re.match(r'\b\d{4}\b', release_info).group()
                if release_info and int(year) == int(release_info):
                    selected_index = i
                    break
        selected_meta = metas[selected_index]
        series_id = selected_meta['imdb_id']
        year = selected_meta.get('releaseInfo')
        year = re.match(r'\b\d{4}\b', year).group()
        series_info = f"{selected_meta['name']} ({year}) {{imdb-{series_id}}}"
        if split:
            shows_dir = "anime_shows" if is_anime(get_moviedb_id(series_id)) else "shows"
        _api_cache[cache_key] = (series_info, series_id, shows_dir)
        return series_info, series_id, shows_dir
    
    if not year:
        if len(metas) > 1 and are_similar(metas[0]['name'], metas[1]['name'], 0.9):
            print(Fore.GREEN + f"Found multiple results for '{series_name}, Year: {year}':")
            for i, meta in enumerate(metas[:3]):
                print(Fore.CYAN + f"{i + 1}: {meta['name']} ({meta.get('releaseInfo', 'Unknown year')})")
                
            selected_index = await aioconsole.ainput(Fore.GREEN + "Enter the number of the correct result (or press Enter to choose the first option): " + Style.RESET_ALL)
            if selected_index.strip().isdigit() and 1 <= int(selected_index) <= len(metas):
                selected_index = int(selected_index) - 1
            else:
                selected_index = 0
        elif len(metas) > 1 and not are_similar(series_name.lower(), metas[0]['name'].lower()) :
            print(Fore.GREEN + f"Found similar or no matching results for '{series_name}':")
            for i, meta in enumerate(metas[:3]):
                print(Fore.CYAN + f"{i + 1}: {meta['name']} ({meta.get('releaseInfo', 'Unknown year')})")
                
            selected_index = await aioconsole.ainput(Fore.GREEN + "Enter the number of your choice, or enter IMDb ID directly:  " + Style.RESET_ALL)
            if selected_index.lower().startswith('tt'):
                url = f"https://v3-cinemeta.strem.io/meta/series/{selected_index}.json"
                response = requests.get(url)
                if response.status_code == 200:
                    show_data = response.json()
                    if 'meta' in show_data and show_data['meta']:
                            show_info = show_data['meta']
                            imdb_id = show_info.get('imdb_id')
                            show_title = show_info.get('name')
                            year_info = show_info.get('releaseInfo')
                            year_info = re.match(r'\b\d{4}\b', year_info).group()
                            series_info = f"{show_title} ({year_info}) {{imdb-{imdb_id}}}"
                            if split:
                                log_message('[DEBUG]', f"dir before: {shows_dir}")
                                shows_dir = "anime_shows" if is_anime(get_moviedb_id(imdb_id)) else "shows"
                            _api_cache[cache_key] = (series_info, imdb_id, shows_dir)
                            return series_info, imdb_id, shows_dir
                    else:
                        print("No show found with the provided IMDb ID")
                        return series_name, None, shows_dir
                else:
                    print("Error fetching show information with IMDb ID")
                    return series_name, None, shows_dir
            elif selected_index.strip().isdigit() and 1 <= int(selected_index) <= len(metas):
                selected_index = int(selected_index) - 1
            else:
                selected_index = 0
        else:
            for i, meta in enumerate(metas):
                if are_similar(series_name.lower().strip(), meta.get('name').lower(), .90):
                    selected_index = i
                    break
    else:
        for i, meta in enumerate(metas):
            release_info = meta.get('releaseInfo')
            release_info = re.match(r'\b\d{4}\b', release_info).group()
            #log_message('DEBUG', f"Name1: {series_name.lower()}, Name2: {meta.get('name')}")
            if are_similar(series_name.lower().strip(), meta.get('name').lower(), .90):
                if release_info and int(year) == int(release_info):
                    selected_index = i
                    break
                else:
                    selected_index = 0

    
    selected_meta = metas[selected_index]
    series_id = selected_meta['imdb_id']
    year = selected_meta.get('releaseInfo')
    year = re.match(r'\b\d{4}\b', year).group()
    series_info = f"{selected_meta['name']} ({year}) {{imdb-{series_id}}}"
    if split:
        shows_dir = "anime_shows" if is_anime(get_moviedb_id(series_id)) else "shows"
    _api_cache[cache_key] = (series_info, series_id, shows_dir)
    return series_info, series_id, shows_dir

def format_multi_match(match):
    log_message('[DEBUG]', F'Match: {match}')
    matched_string = match.group(0)
    if '+' in matched_string or '-' in matched_string:
        matched_string = matched_string.replace(' ', '')
        return matched_string.replace('+', '-').upper()
    parts = re.findall(r'S(\d{2,3})E(\d{2})(E\d{2})', matched_string, re.IGNORECASE)[0]
    return f"S{parts[0]}E{parts[1]}-{parts[2].upper()}"

def get_episode_details(series_id, episode_identifier, name, year):
    
    details_url = f"https://v3-cinemeta.strem.io/meta/series/{series_id}.json"
    #print(details_url)
    response = requests.get(details_url)
    if response.status_code != 200:
        raise Exception(f"Error getting series details: {response.status_code}")
    series_details = response.json()
    if not series_details:
        if year:
            return f"{name} ({year}) - {episode_identifier.lower()}"
        else:
            return f"{name} - {episode_identifier.lower()}"
    meta = series_details.get('meta', [])
    releaseInfo = meta.get('releaseInfo')  
    if releaseInfo is None:
        year = year
    else:
        year = releaseInfo    
    year = re.match(r'\b\d{4}\b', year).group()
    match = re.search(r'(S\d{2,3} ?E\d{2}\-E\d{2})', episode_identifier)
    if match:
        return f"{name} - {episode_identifier.lower()}"
        
    season = int(re.search(r'S(\d{2}) ?E\d{2}', episode_identifier, re.IGNORECASE).group(1))
    episode = int(re.search(r'S(\d{2}) ?E(\d{2,3})', episode_identifier, re.IGNORECASE).group(2))
    
    videos = meta.get('videos', [])
    for video in videos:
        if video['season'] == season and (video.get('episode') == episode or video.get('number') == episode):
            show_name = meta.get('name')
            if show_name is None:
                show_name = name
            if video.get('title') is None:
                title = video.get('name')
            else:
                title = video.get('title')
            return f"{show_name} ({year}) - s{season:02d}e{episode:02d} - {title}"
        
    return f"{meta.get('name')} ({year}) - {episode_identifier.lower()}"

def extract_year(query):
    match = re.search(r'\((\d{4})\)$', query.strip())
    if match:
        return int(match.group(1))
    match = re.search(r'(\d{4})$', query.strip())
    if match:
        return int(match.group(1))
    return None

def extract_year_from_folder(query):
    match = re.search(r'(?<!\w)(\d{4})(?!\w)', query.strip())
    if match:
        return int(match.group(1))
    match = re.search(r'(\d{4})$', query.strip())
    if match:
        return int(match.group(1))
    return None

def extract_resolution(filename):
    # Define patterns to find resolution
    patterns = [
        r'(\d{3,4}p)',    # Matches 720p, 1080p, etc.
        r'(\d{3,4}x\d{3,4})'  # Matches 1920x1080, 1280x720, etc.
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def get_unique_filename(dest_path, new_name):
    base_name, ext = os.path.splitext(new_name)
    counter = 1
    unique_name = new_name
    while os.path.exists(os.path.join(dest_path, unique_name)):
        unique_name = f"{base_name} ({counter}){ext}"
        counter += 1
    return unique_name

async def process_movie(file, foldername, force=False):
    path = f"/{foldername}"
    log_message("[INFO]", f"Current Movie file: {os.path.join(path,file)}")
    
    moviename = re.sub(r'^\[.*?\]\s*', '', foldername)
    moviename = re.sub(r"^\d\. ", "", moviename)
    name, ext = os.path.splitext(file)
    if '.' in moviename:
        moviename = re.sub(r'\.', ' ', moviename)
    pattern = r"^(.*?)\s*[\(\[]?(\d{4})[\)\]]?\s*(?:.*?(\d{3,4}p))?.*$"
    four_digit_numbers = re.findall(r'\b\d{4}\b', moviename)
    if len(four_digit_numbers) >= 2:
        #pattern = r"(.+?)\((\d{4})\)\D+(\d{3,4})(p?)"
        #match = re.search(pattern, moviename)
        log_message('[DEBUG]', f"Moviename: {moviename}")
        log_message('[DEBUG]', f"Four Digit numbers: {four_digit_numbers}")
        title = four_digit_numbers[0]
        year = four_digit_numbers[1]
    else:
        # Search the pattern in the string
        match = re.search(pattern, moviename)
        #log_message('[DEBUG]', f"Match: {match}")
        title = match.group(1)
        year = match.group(2).strip('()')
        #resolution = match.group(3)
    proper_name = await get_movie_info(title, year, force)
    if year is None or year == "":
        if proper_name is None:
            proper_name = title
    else:
        if proper_name is None:
            proper_name = f"{title} ({year})"
    
    return proper_name, ext

async def process_anime(file, pattern1, pattern2, split=False, force=False):
    
    file = re.sub(r'^\[.*?\]\s*', '', file)
    name, ext = os.path.splitext(file)
    
    match = pattern1.match(name)
    
    if match:
        show_name = match.group(1).strip()
        episode_number = match.group(2)
        resolution = match.group(3)
        season_match = re.search(r'S(\d{1})', show_name, re.IGNORECASE)
        special_match = re.search(r'OVA|NCED', show_name)
        if not force:
            if show_name in season_cache:
                season_number = season_cache[show_name]
            elif season_match:
                season_number = season_match.group(1)
            elif special_match:
                season_number = 0
            else:
                log_message('[INFO]', f'Anime Show: {show_name}')
                season_number = await aioconsole.ainput("Enter the season number for the above show: ")
                season_cache[show_name] = season_number
        else:
            if show_name in season_cache:
                season_number = season_cache[show_name]
            elif season_match:
                season_number = season_match.group(1)
            elif special_match:
                season_number = 0
            else:
                season_number = 1
        
        season_match = pattern2.search(file)
        if season_match:
            season_number = int(season_match.group(1))
            show_name = ' '.join(show_name.split(' ')[:-1])
        
        episode_identifier = f"s{int(season_number):02d}e{int(episode_number):03d}"
        show_name, showid, showdir = await get_series_info(show_name.strip(), "", split, force)
        year = re.search(r'\((\d{4})\)', show_name).group(1)
        name = get_episode_details(showid, episode_identifier, show_name, year)
        if resolution:
            name = name.rstrip() + " " + resolution + ext
        else:
            name = name.rstrip() + ext
        show_name = show_name.replace('/', '')
        return show_name, season_number, name, showdir
        


async def process_movie_task(movie_name, movie_folder_name, src_file, dest_dir, existing_symlinks, links_pkl, ignored_files):
    movie_name, ext = await process_movie(movie_name, movie_folder_name)
    movie_name = movie_name.replace("/", " ")
    new_name = movie_name + ext

    dest_path = os.path.join(dest_dir, "movies", movie_name)
    os.makedirs(dest_path, exist_ok=True)
    dest_file = os.path.join(dest_path, new_name)

    if os.path.islink(dest_file):
        if os.readlink(dest_file) == src_file:
            return
        else:
            new_name = get_unique_filename(dest_path, new_name)
            dest_file = os.path.join(dest_path, new_name)
    elif os.path.exists(dest_file) and not os.path.islink(dest_file):
        ignored_files.add(dest_file)
        return

    if os.path.isdir(src_file):
        shutil.copytree(src_file, dest_file, symlinks=True)
    else:
        os.symlink(src_file, dest_file)
        existing_symlinks.add((src_file, dest_file))
        save_link(existing_symlinks, links_pkl)
    
    clean_destination = os.path.basename(dest_file)
    async with print_lock:
        log_message("[SUCCESS]", f"Created symlink: {Fore.LIGHTCYAN_EX}{clean_destination} {Style.RESET_ALL}-> {src_file}")

async def process_movies_in_batches(movies_cache, batch_size=5, ignored_files=None):
    tasks = []
    for movie_name, movie_details in movies_cache.items():
        for movie_folder_name, src_file, dest_dir, existing_symlinks, links_pkl in movie_details:
            tasks.append(process_movie_task(movie_name, movie_folder_name, src_file, dest_dir, existing_symlinks, links_pkl, ignored_files))
            if len(tasks) == batch_size:
                await asyncio.gather(*tasks)
                tasks = []
    if tasks:
        await asyncio.gather(*tasks)

    movies_cache.clear()

async def create_symlinks(src_dir, dest_dir, force=False, split=False):
    os.makedirs(dest_dir, exist_ok=True)
    log_message('[DEBUG]', 'processing...')
    existing_symlinks = load_links(links_pkl)
    ignored_files = load_ignored()
    symlink_created = []
    movies_cache = defaultdict(list)
    
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src_file = os.path.join(root, file)
            is_anime = False
            is_movie = False
            media_dir = "shows"
            symlink_exists = False
            
            if src_file in ignored_files:
               continue
            
            symlink_exists |= any(
                src_file == existing_src_file
                for existing_src_file, _ in existing_symlinks  
            )
            if symlink_exists:
                ignored_files.add(src_file)
                continue
            
            if not src_file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.mpg', '.mpeg', '.m4v', '.ts', '.webm')):
                ignored_files.add(src_file)
                log_message('[WARN]', f"Ignoring file: {src_file}")
                continue
            
            sample_match = re.search(r'sample|trailer|etrg', file, re.IGNORECASE)
            #TODO: Exclude extras like deleted scenes etc
            #extras_match = re.search(r'deleted ?.scenes\b', file, re.IGNORECASE) 
            if sample_match:
                continue

            episode_match = re.search(r'(.*?)(S\d{2}.? ?E\d{2,3}(?:\-E\d{2})?|\b\d{1,2}x\d{2}\b|S\d{2}E\d{2}-?(?:E\d{2})|S\d{2,3} ?E\d{2}(?:\+E\d{2})?)', file, re.IGNORECASE)
            if not episode_match:
                pattern = re.compile(r'(?!.* - \d+\.\d+GB)(.*) - (\d{2,3})(?:v2)?\b(?: (\[?\(?\d{3,4}p\)?\]?))?')
                alt_pattern = re.compile(r'S(\d{1,2}) - (\d{2})')
                if re.search(pattern, file) or re.search(alt_pattern, file):
                    show_folder, season_number, new_name, media_dir = await process_anime(file, pattern, alt_pattern, split, force)
                    season_folder = f"Season {int(season_number):02d}"
                    is_anime = True
                else:
                    continue # you can comment this line to enable the processing of movies
                    is_movie = True
                    movie_folder_name = os.path.basename(root)
                    movies_cache[file].append((movie_folder_name, src_file, dest_dir, existing_symlinks, links_pkl))
                    if len(movies_cache) >= 5:
                        await process_movies_in_batches(movies_cache, ignored_files=ignored_files)
                    continue

            if not is_movie and not is_anime:
                episode_identifier = episode_match.group(2)

                multiepisode_match = re.search(r'(S\d{2,3} ?E\d{2,3}E\d{2}|S\d{2,3} ?E\d{2}\+E\d{2}|S\d{2,3} ?E\d{2}\-E\d{2})', episode_identifier, re.IGNORECASE)
                alt_episode_match = re.search(r'\d{1,2}x\d{2}', episode_identifier)
                edge_case_episode_match = re.search(r'S\d{3} ?E\d{2}', episode_identifier)
                
                if multiepisode_match:
                    episode_identifier = re.sub(
                        r'(S\d{2,3} ?E\d{2}E\d{2}|S\d{2,3} ?E\d{2}\+E\d{2}|S\d{2,3} ?E\d{2}\-E\d{2})',
                        format_multi_match,
                        episode_identifier,
                        flags=re.IGNORECASE
                    )
                elif alt_episode_match:
                    episode_identifier = re.sub(r'(\d{1,2})x(\d{2})', lambda m: f's{int(m.group(1)):02d}e{m.group(2)}', episode_identifier)
                elif edge_case_episode_match:
                    episode_identifier = re.sub(r'S(\d{3}) ?E(\d{2})', lambda m: f's{int(m.group(1)):d}e{m.group(2)}', episode_identifier)
                    
                parent_folder_name = os.path.basename(root)
                folder_name = re.sub(r'\s*(S\d{2}.*|Season \d+).*|(\d{3,4}p)', '', parent_folder_name).replace('-', ' ').replace('.', ' ')
                
                if re.match(r'S\d{2} ?E\d{2}', file, re.IGNORECASE):
                    show_name = re.sub(r'\s*(S\d{2}.*|Season \d+).*', '', parent_folder_name).replace('-', ' ').replace('.', ' ').strip()
                else:
                    show_name = episode_match.group(1).replace('.', ' ').strip()
                
                if are_similar(folder_name.lower(), show_name.lower()):
                    show_name = folder_name    

                name, ext = os.path.splitext(file)
                
                if '.' in name:
                    new_name = re.sub(r'\.', ' ', name)
                else:
                    new_name = name

                if '.' in episode_identifier:
                    episode_identifier = re.sub(r'\.', ' ', episode_identifier)
                season_number = re.search(r'S(\d{2}) ?E\d{2,3}', episode_identifier, re.IGNORECASE).group(1)
                season_folder = f"Season {int(season_number):02d}"
                
                show_folder = re.sub(r'\s+$|_+$|-+$|(\()$', '', show_name).rstrip()

                if show_folder.isdigit() and len(show_folder) <= 4:
                    year = None
                else:
                    year = extract_year_from_folder(parent_folder_name) or extract_year(show_folder)
                    if year:
                        show_folder = re.sub(r'\(\d{4}\)$', '', show_folder).strip()
                        show_folder = re.sub(r'\d{4}$', '', show_folder).strip()       
                show_folder, showid, media_dir = await get_series_info(show_folder, year, split, force)
                show_folder = show_folder.replace('/', '')
                
                resolution = extract_resolution(new_name)
                if not resolution:
                    resolution = extract_resolution(parent_folder_name)
                    if resolution is not None:
                        resolution = f"{resolution}"
                        
                file_name = re.search(r'(^.*S\d{2}E\d{2})', new_name)
                if file_name:
                    new_name = file_name.group(0) + ' '
                if re.search(r'\{(tmdb-\d+|imdb-tt\d+)\}', show_folder):
                    year = re.search(r'\((\d{4})\)', show_folder).group(1)
                    new_name = get_episode_details(showid, episode_identifier, show_folder, year)
                
                if resolution:
                    new_name = new_name.rstrip() + " " + resolution + ext
                else: 
                    new_name = new_name.rstrip() + ext

            new_name = new_name.replace('/', '')
            dest_path = os.path.join(dest_dir, media_dir, show_folder, season_folder)
                    
            os.makedirs(dest_path, exist_ok=True)
            dest_file = os.path.join(dest_path, new_name)
            if os.path.islink(dest_file):
                if os.readlink(dest_file) == src_file:
                    continue
                else:
                    new_name = get_unique_filename(dest_path, new_name)
                    dest_file = os.path.join(dest_path, new_name)
            
            if os.path.exists(dest_file) and not os.path.islink(dest_file):
                ignored_files.add(dest_file)
                continue

            if os.path.isdir(src_file):
                shutil.copytree(src_file, dest_file, symlinks=True)
            else:
                try:
                    os.symlink(src_file, dest_file)
                except OSError as e:
                    if e.errno == 36:  # File name too long
                        short_name = re.sub(r"(s\d{2}e\d{2}).*\.(\w+)$", r"\1.\2", new_name, flags=re.IGNORECASE) 
                        dest_file = os.path.join(dest_path, short_name)
                        print(dest_file)
                        os.symlink(src_file, dest_file)
                    else:
                        raise
                existing_symlinks.add((src_file, dest_file))
                save_link(existing_symlinks, links_pkl)
                symlink_created.append(dest_file)
                
            clean_destination = os.path.basename(dest_file)
            log_message("[SUCCESS]", f"Created symlink: {Fore.LIGHTCYAN_EX}{clean_destination} {Style.RESET_ALL}-> {src_file}")

    if movies_cache:
        await process_movies_in_batches(movies_cache, ignored_files=ignored_files)

    save_ignored(ignored_files)
    return symlink_created

async def main():
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Create symlinks for files from src_dir in dest_dir.")
    parser.add_argument("--split-dirs", action="store_true", help="Use separate directories for anime")
    parser.add_argument("--loop", action="store_true", help="When this is used, the script will periodically scan the source directory and automatically choose the first result when querying movies and/or shows")
    args = parser.parse_args()
    force = False
    apikey = get_api_key()
    
    if args.split_dirs:
        if apikey is None or apikey == "" or apikey == "null":
            apikey = prompt_for_api_key()
        
    if 'src_dir' not in settings or 'dest_dir' not in settings:
        log_message("[INFO]", f"Missing configuration in settings.json. Please provide necessary inputs.{Style.RESET_ALL}")
        src_dir, dest_dir = prompt_for_settings(apikey)
    else:
        src_dir = settings['src_dir']
        dest_dir = settings['dest_dir']
        
    if args.loop:
        force = True
        while True:
            if await create_symlinks(src_dir, dest_dir, force, split=args.split_dirs):
                log_message('[SUCCESS]', 'Attempting to update Plex Library sections')
                command = ['python3', 'scan_plex.py', dest_dir]
                try:
                    subprocess.run(command, check=True)
                except subprocess.CalledProcessError as e:
                    log_message('ERROR', f"Error running scan_plex.py: {e}")
            log_message('[INFO]', "Sleeping for 2 minutes before next run...")
            time.sleep(120)
    else:
        if await create_symlinks(src_dir, dest_dir, force, split=args.split_dirs):
            log_message('[SUCCESS]', 'Attempting to update Plex Library sections')
            command = ['python3', 'scan_plex.py', dest_dir]
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as e:
                log_message('ERROR', f"Error running scan_plex.py: {e}")

if __name__ == "__main__":
    asyncio.run(main())
