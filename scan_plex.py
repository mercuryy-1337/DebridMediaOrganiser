import os
import subprocess
import requests
import xml.etree.ElementTree as ET
import json
import argparse

def get_plex_config():
    """Retrieve Plex configuration from plex.json."""
    try:
        with open('plex.json', 'r') as file:
            config = json.load(file)
        return config
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        raise Exception("Error decoding plex.json.")

def prompt_for_config():
    """Prompt user for Plex configuration details."""
    plex_host = input("Enter Plex host (e.g., localhost or IP of server): ").strip()
    plex_port = input("Enter Plex port (e.g., 32400): ").strip()
    plex_token = input("Enter Plex token: ").strip()

    return plex_host, plex_port, plex_token

def save_plex_config(plex_host, plex_port, plex_token):
    config = {
        'plex_url': f'http://{plex_host}:{plex_port}',
        'plex_token': plex_token
    }
    with open('plex.json', 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=4)

def ensure_plex_config():
    """Ensure plex.json exists and is properly configured."""
    config = get_plex_config()
    if config is None:
        print("Configuration file not found or empty.")
        plex_host, plex_port, plex_token = prompt_for_config()
        save_plex_config(plex_host, plex_port, plex_token)
    else:
        plex_host = config.get('plex_url', '').replace('http://', '').split(':')[0]
        plex_port = config.get('plex_url', '').replace('http://', '').split(':')[1] if ':' in config.get('plex_url', '') else ''
        plex_token = config.get('plex_token', '')

        if not plex_host or not plex_port or not plex_token:
            print("Some configuration details are missing or incomplete.")
            plex_host, plex_port, plex_token = prompt_for_config()
            save_plex_config(plex_host, plex_port, plex_token)

    return f'http://{plex_host}:{plex_port}', plex_token

def get_plex_library_sections(plex_url, plex_token):
    """Retrieve the list of library sections from Plex."""
    url = f"{plex_url}/library/sections?X-Plex-Token={plex_token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve library sections: {response.status_code}")
    
    try:
        root = ET.fromstring(response.content)
        sections = {}
        for directory in root.findall('.//Directory'):
            title = directory.get('title')
            key = directory.get('key')
            locations = [loc.get('path') for loc in directory.findall('./Location')]
            sections[key] = {'title': title, 'locations': locations, "key": key}
        return sections
    except ET.ParseError as e:
        raise Exception(f"Failed to parse library sections response: {e}")

def scan_plex_library_sections(src_dir, plex_url, plex_token):
    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory '{src_dir}' does not exist or is not a directory.")

    subdirs = [os.path.join(src_dir, d) for d in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, d))]
    try:
        sections = get_plex_library_sections(plex_url, plex_token)
    except Exception as e:
        print(f"Failed to retrieve library sections from Plex: {e}")
        return

    for subdir in subdirs:
        section_id = None
        for key, info in sections.items():
            if 'locations' in info and subdir in info['locations']:
                section_id = key

        if not section_id:
            print(f"No matching library section found in Plex for: {subdir}, please ensure directory exists and is mapped to a Plex library")
            continue

        curl_command = (
            f'curl '
            f'"{plex_url}/library/sections/{section_id}/refresh?X-Plex-Token={plex_token}"'
        )

        try:
            subprocess.run(curl_command, shell=True, check=True)
            print(f"Successfully scanned library section: {subdir}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to scan library section: {subdir}. Error: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan Plex library sections.')
    parser.add_argument('src_dir', type=str, help='Source directory to scan.')
    
    args = parser.parse_args()
    
    plex_url, plex_token = ensure_plex_config()

    scan_plex_library_sections(args.src_dir, plex_url, plex_token)
