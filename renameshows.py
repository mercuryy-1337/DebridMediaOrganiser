import os
import argparse
import re
import shutil
import requests
import json
import time
from functools import lru_cache
from colorama import init, Fore, Style

init(autoreset=True)

SETTINGS_FILE = 'settings.json'
_api_cache = {}

LOG_LEVELS = {
    "SUCCESS": {"level": 10, "color": Fore.LIGHTGREEN_EX},
    "INFO": {"level": 20, "color": Fore.BLUE},
    "ERROR": {"level": 30, "color": Fore.RED},
    "WARN": {"level": 40, "color": Fore.YELLOW},
    "DEBUG": {"level": 50, "color": Fore.LIGHTMAGENTA_EX}
}

def log_message(log_level, message):
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    if log_level in LOG_LEVELS:
        log_info = LOG_LEVELS[log_level]
        formatted_message = f"{Fore.WHITE}{current_time} | {log_info['color']}{log_level} {Fore.WHITE}| {log_info['color']}{message}"
        colored_message = f"{log_info['color']}{formatted_message}{Style.RESET_ALL}"
        print(colored_message)
    else:
        print(f"Unknown log level: {log_level}")

def get_api_key():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            settings = json.load(file)
            return settings.get('api_key')
    return None

def save_settings(api_key, src_dir, dest_dir, id):
    settings = {
        'api_key': api_key,
        'src_dir': src_dir,
        'dest_dir': dest_dir,
        'id': id
    }
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file)

def prompt_for_api_key():
    api_key = input("Please enter your TMDb API key: ")
    return api_key

def prompt_for_settings():
    if 'api_key' not in settings or not settings['api_key']:
        api_key = prompt_for_api_key()
    src_dir = input("Enter the source directory path: ")
    dest_dir = input("Enter the destination directory path: ")
    id_choice = input("Choose id (tmdb or imdb): ").strip().lower()
    while id_choice not in ['tmdb', 'imdb']:
        id_choice = input("Invalid choice. Choose id (tmdb or imdb): ").strip().lower()
    save_settings(api_key, src_dir, dest_dir, id_choice)
    return src_dir, dest_dir, id_choice

def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            return json.load(file)
    return {}

def get_imdb_id(tmdb_id):
    api_key = get_api_key()
    if not api_key:
        api_key = prompt_for_api_key()

    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids"
    params = {
        'api_key': api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        external_ids = response.json()
        imdb_id = external_ids.get('imdb_id')
        return imdb_id
    except requests.exceptions.RequestException as e:
        log_message("ERROR",f"Error fetching IMDb ID for TMDb ID {tmdb_id}: {e}")
        return None

@lru_cache(maxsize=None)
def search_tv_show(query, year=None, id='tmdb', force=False):
    cache_key = (query, year, id)
    if cache_key in _api_cache:
        return _api_cache[cache_key]

    api_key = get_api_key()
    if not api_key:
        api_key = prompt_for_api_key()

    url = "https://api.themoviedb.org/3/search/tv"

    params = {
        'api_key': api_key,
        'query': query
    }
    # Add the year parameter if provided
    if year:
        params['first_air_date_year'] = year

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])

        if results:
            chosen_show = results[0] if force else None

            if not force and len(results) == 1:
                chosen_show = results[0]

            if chosen_show:
                show_name = chosen_show.get('name')
                show_id = chosen_show.get('id')
                first_air_date = chosen_show.get('first_air_date')
                show_year = first_air_date.split('-')[0] if first_air_date else "Unknown Year"
                tmdb_id = chosen_show.get('id')
                imdb_id = get_imdb_id(tmdb_id) if id == 'imdb' else None
                if id == 'tmdb':
                    proper_name = f"{show_name} ({show_year}) {{tmdb-{tmdb_id}}}"
                elif id == 'imdb' and imdb_id:
                    proper_name = f"{show_name} ({show_year}) {{imdb-{imdb_id}}}"
                else:
                    proper_name = f"{show_name} ({show_year})"
                _api_cache[cache_key] = proper_name
                #log_message("DEBUG",proper_name)
                return proper_name
            else:
                print(Fore.YELLOW + f"Original file/show name: {query} year={year}")

                # Show the first 3 results and let the user choose one
                for idx, show in enumerate(results[:3]):
                    show_name = show.get('name')
                    show_id = show.get('id')
                    first_air_date = show.get('first_air_date')
                    show_year = first_air_date.split('-')[0] if first_air_date else "Unknown Year"
                    print(Fore.CYAN + f"{idx + 1}: {show_name} ({show_year}) [tmdb-{show_id}]")

                if not force:
                    choice = input(Fore.GREEN + "Choose a show (1-3) or press Enter to skip: " + Style.RESET_ALL).strip()

                    if choice.isdigit() and 1 <= int(choice) <= 3:
                        chosen_show = results[int(choice) - 1]

                if chosen_show:
                    show_name = chosen_show.get('name')
                    show_id = chosen_show.get('id')
                    first_air_date = chosen_show.get('first_air_date')
                    show_year = first_air_date.split('-')[0] if first_air_date else "Unknown Year"
                    tmdb_id = chosen_show.get('id')
                    imdb_id = get_imdb_id(tmdb_id) if id == 'imdb' else None
                    if id == 'tmdb':
                        proper_name = f"{show_name} ({show_year}) {{tmdb-{tmdb_id}}}"
                    elif id == 'imdb' and imdb_id:
                        proper_name = f"{show_name} ({show_year}) {{imdb-{imdb_id}}}"
                    else:
                        proper_name = f"{show_name} ({show_year})"
                    _api_cache[cache_key] = proper_name
                    #log_message("DEBUG",f"Selected show: {proper_name}")
                    return proper_name
                else:
                    _api_cache[cache_key] = f"{query}"
                    return f"{query}"
        else:
            _api_cache[cache_key] = f"{query}"
            return f"{query}"

    except requests.exceptions.RequestException as e:
        log_message("ERROR",f"Error fetching data: {e}")

def extract_year(query):
    match = re.search(r'\((\d{4})\)$', query.strip())
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

def extract_resolution_from_folder(folder_name):
    # Define patterns to find resolution in folder name
    patterns = [
        r'(\d{3,4}p)',    # Matches 720p, 1080p, etc.
        r'(\d{3,4}x\d{3,4})'  # Matches 1920x1080, 1280x720, etc.
    ]
    for pattern in patterns:
        match = re.search(pattern, folder_name, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def extract_folder_year(folder_name):
    match = re.search(r'\((\d{4})\)', folder_name)
    if match:
        return int(match.group(1))
    match = re.search(r'\.(\d{4})\.', folder_name)
    if match:
        return int(match.group(1))
    return None

def create_symlinks(src_dir, dest_dir, force=False, id='tmdb'):
    os.makedirs(dest_dir, exist_ok=True)

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src_file = os.path.join(root, file)
            
            symlink_exists = False
            # Check if there's a symlink attached to the file before continuing
            for dirpath, _, filenames in os.walk(dest_dir):
                for filename in filenames:
                    full_dest_file = os.path.join(dirpath, filename)
                    if os.path.islink(full_dest_file) and os.readlink(full_dest_file) == src_file:
                        symlink_exists = True
                        #log_message("DEBUG",f"Skipping file: {Style.RESET_ALL}{src_file}")
                        break
                if symlink_exists:
                    break
            
            if symlink_exists:
                continue
            
            episode_match = re.search(r'(.*?)(S\d{2} ?E\d{2})', file, re.IGNORECASE)
            if not episode_match:
                log_message("WARN",f"Skipping file without S00E00 pattern: {Style.RESET_ALL}{file}")
                continue

            episode_identifier = episode_match.group(2)
            parent_folder_name = os.path.basename(root)
            
            if re.match(r'S\d{2} ?E\d{2}', file, re.IGNORECASE):
                show_name = re.sub(r'\s*(S\d{2}.*|Season \d+).*', '', parent_folder_name).replace('-', ' ').replace('.', ' ').strip()
            else:
                show_name = episode_match.group(1).replace('.', ' ').strip()

            name, ext = os.path.splitext(file)
            
            if '.' in name:
                new_name = re.sub(r'\.', ' ', name)
            else:
                new_name = name
            
            resolution = extract_resolution(new_name)
            #log_message("DEBUG", f"Resolution from file = {resolution}")
            if not resolution:
                resolution = extract_resolution_from_folder(parent_folder_name)
                #log_message("DEBUG",f"Resolution from folder = {resolution}")
                if resolution is not None:
                    resolution = f" {resolution}"
            if resolution:
                split_name = new_name.split(resolution)[0]
                if split_name.endswith("("):
                    new_name = split_name[:-1] + resolution + ext
                    #log_message("DEBUG",f"symlink name: {new_name}")
                else:
                    new_name = split_name + resolution + ext
                    #log_message("DEBUG",f"symlink name: {new_name}")
            else:
                new_name += ext

            season_number = re.search(r'S(\d{2}) ?E\d{2}', episode_identifier, re.IGNORECASE).group(1)
            season_folder = f"Season {int(season_number)}"
            
            show_folder = re.sub(r'\s+$|_+$|-+$|(\()$', '', show_name)
            show_folder = show_folder.rstrip()
            
            if show_folder.isdigit() and len(show_folder) <= 4:
                year = None
            else:
                year = extract_folder_year(parent_folder_name) or extract_year(show_folder)
                if year:
                    show_folder = re.sub(r'\(\d{4}\)$', '', show_folder).strip()
                    show_folder = re.sub(r'\d{4}$', '', show_folder).strip()
            
            show_folder = search_tv_show(show_folder, year, id=id, force=force)
            show_folder = show_folder.replace('/', '')
            dest_path = os.path.join(dest_dir, show_folder, season_folder)
            os.makedirs(dest_path, exist_ok=True)
            
            dest_file = os.path.join(dest_path, new_name)
            
            if os.path.islink(dest_file):
                if os.readlink(dest_file) == src_file:
                    continue
                else:
                    os.remove(dest_file)
            
            if os.path.exists(dest_file) and not os.path.islink(dest_file):
                continue

            if os.path.isdir(src_file):
                shutil.copytree(src_file, dest_file, symlinks=True)
            else:
                os.symlink(src_file, dest_file)
            clean_destination = os.path.basename(dest_file)
            log_message("SUCCESS",f"Created symlink: {Fore.LIGHTCYAN_EX}{clean_destination} {Style.RESET_ALL}-> {src_file}")

if __name__ == "__main__":
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Create symlinks for files from src_dir in dest_dir.")
    parser.add_argument("--force", action="store_true", help="Disregards user input and automatically chooses the first option")
    args = parser.parse_args()
    
    if 'src_dir' not in settings or 'dest_dir' not in settings or 'id' not in settings:
        log_message("INFO",f"Missing configuration in settings.json. Please provide necessary inputs.{Style.RESET_ALL}")
        src_dir, dest_dir, id_choice = prompt_for_settings()
    else:
        src_dir = settings['src_dir']
        dest_dir = settings['dest_dir']
        id_choice = settings['id']

    create_symlinks(src_dir, dest_dir, force=args.force, id=id_choice)
