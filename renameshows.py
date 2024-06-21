import os
import argparse
import re
import shutil
import requests
import json
from functools import lru_cache

SETTINGS_FILE = 'settings.json'
_api_cache = {}

def get_api_key():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as file:
            settings = json.load(file)
            return settings.get('api_key')
    return None

def save_api_key(api_key):
    settings = {'api_key': api_key}
    with open(SETTINGS_FILE, 'w') as file:
        json.dump(settings, file)

def prompt_for_api_key():
    api_key = input("Please enter your TMDb API key: ")
    save_api_key(api_key)
    return api_key

# Function to search for TV shows on TMDb and return the show name, id etc
@lru_cache(maxsize=None)
def search_tv_show(query, year=None):
    cache_key = (query, year)
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
            # Get the first result (very high success rate so i'm keeping it this way)
            show = results[0]
            show_name = show.get('name')
            show_id = show.get('id')
            first_air_date = show.get('first_air_date')
            show_year = first_air_date.split('-')[0] if first_air_date else "Unknown Year"
            proper_name = f"{show_name} ({show_year}) {{tmdb-{show_id}}}"
            _api_cache[cache_key] = proper_name
            return proper_name
        else:
            _api_cache[cache_key] = f"{query}"
            return f"{query}"

    except requests.exceptions.RequestException as e:
        return f"Error fetching data: {e}"

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

def create_symlinks(src_dir, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src_file = os.path.join(root, file)
            
            episode_match = re.search(r'(.*?)(S\d{2}E\d{2})', file, re.IGNORECASE)
            if not episode_match:
                print(f"Skipping file without S00E00 pattern: {file}")
                continue

            episode_identifier = episode_match.group(2)
            
            if re.match(r'S\d{2}E\d{2}', file, re.IGNORECASE):
                parent_folder_name = os.path.basename(root)
                show_name = re.sub(r'\s*(S\d{2}.*|Season \d+).*', '', parent_folder_name).replace('-', ' ').replace('.', ' ').strip()
            else:
                show_name = episode_match.group(1).replace('.', ' ').strip()

            name, ext = os.path.splitext(file)
            
            if '.' in name:
                new_name = re.sub(r'\.', ' ', name)
            else:
                new_name = name
            
            resolution = extract_resolution(new_name)
            if resolution:
                split_name = new_name.split(resolution)[0]
                if split_name.endswith("("):
                    new_name = split_name[:-1] + resolution + ext
                else:
                    new_name = split_name + resolution + ext
            else:
                new_name += ext

            season_number = re.search(r'S(\d{2})E\d{2}', episode_identifier, re.IGNORECASE).group(1)
            season_folder = f"Season {int(season_number)}"
            
            show_folder = re.sub(r'\s+$|_+$|-+$|(\()$', '', show_name)
            show_folder = show_folder.rstrip()
            
            if show_folder.isdigit() and len(show_folder) <= 4:
                year = None
            else:
                year = extract_year(show_folder)
                if year:
                    show_folder = re.sub(r'\(\d{4}\)$', '', show_folder).strip()
                    show_folder = re.sub(r'\d{4}$', '', show_folder).strip()
            
            show_folder = search_tv_show(show_folder, year)
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
                print(f"Skipping existing file: {dest_file}")
                continue

            if os.path.isdir(src_file):
                shutil.copytree(src_file, dest_file, symlinks=True)
            else:
                os.symlink(src_file, dest_file)
            print(f"Created symlink: {dest_file} -> {src_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create symlinks for files from src_dir in dest_dir.")
    parser.add_argument("src_dir", type=str, help="Source directory to search for files")
    parser.add_argument("dest_dir", type=str, help="Destination directory to place symlinks")
    args = parser.parse_args()

    create_symlinks(args.src_dir, args.dest_dir)
