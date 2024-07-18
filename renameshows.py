import os
import argparse
import re
import shutil
import requests
import json
import time
import difflib
import pickle
import subprocess
from functools import lru_cache
from colorama import init, Fore, Style

init(autoreset=True)

SETTINGS_FILE = 'settings.json'
links_pkl = 'symlinks.pkl'
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

def are_similar(folder_name, show_name, threshold=0.8):
    """Check if the folder name is mostly the same as the show name"""
    similarity = difflib.SequenceMatcher(None, folder_name, show_name).ratio()
    return similarity >= threshold

def get_api_key():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            settings = json.load(file)
            return settings.get('api_key')
    return None

def save_link(data, file_path):
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

def load_links(file_path):
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return set()

def save_settings(api_key, src_dir, dest_dir):
    settings = {
        'api_key': api_key,
        'src_dir': src_dir,
        'dest_dir': dest_dir,
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
    dest_dir = input("Enter the destination directory path (Path to riven's show directoy e.g /mnt/riven/shows): \n")
    save_settings(api_key, src_dir, dest_dir)
    return src_dir, dest_dir

def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            return json.load(file)
    return {}

def get_imdb_id(tmdb_id, api_key):
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={api_key}"

    # Make the GET request
    response = requests.get(url)

    # Check if request was successful (status code 200)
    if response.status_code == 200:
        # Parse JSON response
        tv_show_info = response.json()

        # Check if IMDb ID is available in the response
        if 'imdb_id' in tv_show_info:
            return tv_show_info['imdb_id']
        else:
            print("IMDb ID not found for this TV show.")
            return None
    else:
        print(f"Error accessing TMDb API. Status code: {response.status_code}")
        return None

@lru_cache(maxsize=None)
def search_tv_show(query, year=None, force=False):
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
    if year:
        params['first_air_date_year'] = year

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])

        if results:
            #log_message('DEBUG',f'{query}')
            chosen_show = results[0] if force else None

            if not force and len(results) == 1:
                chosen_show = results[0]   
                
            if year is not None:
                chosen_show = results[0]    

            if chosen_show:
                show_name = chosen_show.get('name')
                show_id = chosen_show.get('id')
                imdb_id = get_imdb_id(show_id,api_key)
                first_air_date = chosen_show.get('first_air_date')
                show_year = first_air_date.split('-')[0] if first_air_date else "Unknown Year"
                if show_id:
                    proper_name = f"{show_name} ({show_year}) {{imdb-{imdb_id}}}"
                else:
                    proper_name = f"{show_name} ({show_year})"
                _api_cache[cache_key] = (proper_name, show_id)  # Store as tuple
                return proper_name, show_id
            else:
                print(Fore.YELLOW + f"Original file/show name: {query} year={year}")

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
                    imdb_id = get_imdb_id(show_id,api_key)
                    first_air_date = chosen_show.get('first_air_date')
                    show_year = first_air_date.split('-')[0] if first_air_date else "Unknown Year"
                    if show_id:
                        proper_name = f"{show_name} ({show_year}) {{imdb-{imdb_id}}}"
                    else:
                        proper_name = f"{show_name} ({show_year})"
                    _api_cache[cache_key] = (proper_name, show_id)  # Store as tuple
                    return proper_name, show_id
                else:
                    _api_cache[cache_key] = (f"{query}", "")
                    return f"{query}", ""
        else:
            _api_cache[cache_key] = (f"{query}", "")
            return f"{query}", ""

    except requests.exceptions.RequestException as e:
        log_message("ERROR", f"Error fetching data: {e}")
        return f"{query}", ""

def format_multi_match(match):
    log_message('DEBUG', F'Match: {match}')
    matched_string = match.group(0)
    if '+' in matched_string or '-' in matched_string:
        matched_string = matched_string.replace(' ', '')
        return matched_string.replace('+', '-').upper()
    parts = re.findall(r'S(\d{2,3})E(\d{2})(E\d{2})', matched_string, re.IGNORECASE)[0]
    return f"S{parts[0]}E{parts[1]}-{parts[2].upper()}"

def get_episode_details(show_id, show_name, episode_identifier, api_key, simple=False):
    match = re.search('(S\d{2,3} ?E\d{2}\-E\d{2})', episode_identifier)
    if match:
        return f"{show_name} - {episode_identifier} "
        
    season_number = int(re.search(r'S(\d{2}) ?E\d{2}', episode_identifier, re.IGNORECASE).group(1))
    episode_number = int(re.search(r'S(\d{2}) ?E(\d{2})', episode_identifier, re.IGNORECASE).group(2))
    
    if simple:
        formatted_episode_number = f"S{season_number:02d}E{episode_number:02d} "
        return f"{show_name} - {formatted_episode_number}"
    season_details_url = f"https://api.themoviedb.org/3/tv/{show_id}/season/{season_number}"
    try:
        season_response = requests.get(season_details_url, params={'api_key': api_key})
        season_response.raise_for_status()

        episodes = season_response.json().get('episodes', [])
        episode = next((ep for ep in episodes if ep['episode_number'] == episode_number), None)

        if episode:
            episode_name = episode['name']
            formatted_episode_number = f"S{season_number:02d}E{episode_number:02d}"
            return f"{show_name} - {formatted_episode_number} - {episode_name} "
        else:
            formatted_episode_number = f"S{season_number:02d}E{episode_number:02d} "
            return f"{show_name} - {formatted_episode_number}"

    except requests.exceptions.RequestException as e:
        log_message('ERROR',f"Error fetching episode: {e}")
        formatted_episode_number = f"S{season_number:02d}E{episode_number:02d} "
        return f"{show_name} - {formatted_episode_number}"

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

def create_symlinks(src_dir, dest_dir, force=False, simple=False):
    os.makedirs(dest_dir, exist_ok=True)
    log_message('DEBUG','processing...')
    existing_symlinks = load_links(links_pkl)
    symlink_created = []
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src_file = os.path.join(root, file)
            
            symlink_exists = False
             # Check if symlink exists based on previously created symlinks (from media.pkl)
            symlink_exists |= any(
                src_file == existing_src_file
                for existing_src_file, _ in existing_symlinks
                
            )

            if symlink_exists:
                continue
            sample_match = re.search('sample', file, re.IGNORECASE)
            if sample_match:
                log_message('WARN',f'Skipping sample file: {file}')
                continue
            episode_match = re.search(r'(.*?)(S\d{2} E\d{2,3}(?:\-E\d{2})?|\d{1,2}x\d{2}|S\d{2}E\d{2}-?(?:E\d{2})|S\d{2,3} ?E\d{2}(?:\+E\d{2})?)', file, re.IGNORECASE)
            if not episode_match:
                #log_message("WARN",f"Skipping file without S00E00 pattern: {Style.RESET_ALL}{file}")
                continue
            episode_identifier = episode_match.group(2)
            
            multiepisode_match = re.search(r'(S\d{2,3} ?E\d{2,3}E\d{2}|S\d{2,3} ?E\d{2}\+E\d{2}|S\d{2,3} ?E\d{2}\-E\d{2})', episode_identifier, re.IGNORECASE)
            alt_episode_match = re.search(r'\d{1,2}x\d{2}', episode_identifier)
            edge_case_episode_match = re.search(r'S\d{3} ?E\d{2}',episode_identifier)
            #log_message('DEBUG',f'Identified episode: {episode_identifier}')
            if multiepisode_match:
                #log_message('DEBUG',f'Identifier before: {episode_identifier}')
                episode_identifier = re.sub(
                    r'(S\d{2,3} ?E\d{2}E\d{2}|S\d{2,3} ?E\d{2}\+E\d{2}|S\d{2,3} ?E\d{2}\-E\d{2})',
                    format_multi_match,
                    episode_identifier,
                    flags=re.IGNORECASE
                )
                #log_message('DEBUG', f'After: {episode_identifier}')
            elif alt_episode_match:
                episode_identifier = re.sub(r'(\d{1,2})x(\d{2})', r'S\2E\2', episode_identifier)
            elif edge_case_episode_match:
                episode_identifier = re.sub(r'S(\d{3}) ?E(\d{2})', lambda m: f'S{int(m.group(1)):d}E{m.group(2)}', episode_identifier)
            
            #log_message('DEBUG',f'Identifier: {episode_identifier}')    
                
            parent_folder_name = os.path.basename(root)
            folder_name = re.sub(r'\s*(S\d{2}.*|Season \d+).*|(\d{3,4}p)', '', parent_folder_name).replace('-',' ').replace('.',' ')
            #log_message('DEBUG',f'Folder: {folder_name}')
            #log_message('DEBUG',f'parent folder: {parent_folder_name}')
            if re.match(r'S\d{2} ?E\d{2}', file, re.IGNORECASE):
                show_name = re.sub(r'\s*(S\d{2}.*|Season \d+).*', '', parent_folder_name).replace('-', ' ').replace('.', ' ').strip()
                #log_message('DEBUG',f'showname: {show_name}')
            else:
                show_name = episode_match.group(1).replace('.', ' ').strip()
                #log_message('DEBUG',f'showname2: {show_name}')
              
            if are_similar(folder_name.lower(),show_name.lower()):
                show_name = folder_name    

            name, ext = os.path.splitext(file)
            
            if '.' in name:
                new_name = re.sub(r'\.', ' ', name)
            else:
                new_name = name

            season_number = re.search(r'S(\d{2}) ?E\d{2,3}', episode_identifier, re.IGNORECASE).group(1)
            season_folder = f"Season {int(season_number)}"
            
            
            show_folder = re.sub(r'\s+$|_+$|-+$|(\()$', '', show_name)
            show_folder = show_folder.rstrip()

            if show_folder.isdigit() and len(show_folder) <= 4:
                year = None
            else:
                year = extract_year_from_folder(parent_folder_name) or extract_year(show_folder)
                if year:
                    show_folder = re.sub(r'\(\d{4}\)$', '', show_folder).strip()
                    show_folder = re.sub(r'\d{4}$', '', show_folder).strip()
                    
            show_folder, showid = search_tv_show(show_folder, year, force=force)

            show_folder = show_folder.replace('/', '')
            
            resolution = extract_resolution(new_name)
            #log_message("DEBUG", f"Resolution from file = {resolution}")
            if not resolution:
                resolution = extract_resolution(parent_folder_name)
                #log_message("DEBUG",f"Resolution from folder = {resolution}")
                if resolution is not None:
                    resolution = f"{resolution}"
            #log_message('DEBUG',f'{show_folder} - {year} {episode_identifier}{ext}')
            file_name = re.search(r'(^.*S\d{2}E\d{2})',new_name)
            if file_name:
                new_name = file_name.group(0) + ' '
            if re.search('\{(tmdb-\d+|imdb-tt\d+)\}', show_folder):
                year = re.search('\((\d{4})\)',show_folder).group(1)
                episode_name = re.sub('\{(tmdb-\d+|imdb-tt\d+)\}','',show_folder).strip()
                new_name = get_episode_details(showid,episode_name,episode_identifier,get_api_key(),simple)
                #log_message('DEBUG',)
                
                
            if resolution:
                split_name = new_name.split(resolution)[0]
                if split_name.endswith("("):
                    new_name = split_name[:-1] + resolution + ext
                else:
                    new_name = split_name + resolution + ext
            else:
                new_name = new_name.rstrip() + ext
                
            new_name = new_name.replace('/','')
            dest_path = os.path.join(dest_dir, show_folder, season_folder)
            os.makedirs(dest_path, exist_ok=True)
            
            dest_file = os.path.join(dest_path, new_name)
            if os.path.islink(dest_file):
                if os.readlink(dest_file) == src_file:
                    continue
                else:
                    new_name = get_unique_filename(dest_path,new_name)
                    dest_file = os.path.join(dest_path, new_name)
            
            if os.path.exists(dest_file) and not os.path.islink(dest_file):
                continue

            if os.path.isdir(src_file):
                shutil.copytree(src_file, dest_file, symlinks=True)
            else:
                os.symlink(src_file, dest_file)
                existing_symlinks.add((src_file, dest_file))
                save_link(existing_symlinks, links_pkl)
                symlink_created.append(dest_file)
            clean_destination = os.path.basename(dest_file)
            log_message("SUCCESS",f"Created symlink: {Fore.LIGHTCYAN_EX}{clean_destination} {Style.RESET_ALL}-> {src_file}")
    return symlink_created
            

if __name__ == "__main__":
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Create symlinks for files from src_dir in dest_dir.")
    parser.add_argument("--simple", action="store_true", help= "Individual episodes will not be queried through TMDb, will be renamed in a simple format")
    args = parser.parse_args()
    
    if 'src_dir' not in settings or 'dest_dir' not in settings:
        log_message("INFO",f"Missing configuration in settings.json. Please provide necessary inputs.{Style.RESET_ALL}")
        src_dir, dest_dir = prompt_for_settings()
    else:
        src_dir = settings['src_dir']
        dest_dir = settings['dest_dir']

    if create_symlinks(src_dir, dest_dir, force=False, simple=args.simple):
        log_message('SUCCESS', 'All Symlinks have been created!')
