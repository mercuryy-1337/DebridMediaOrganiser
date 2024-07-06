#!/bin/bash

# PLEX PARTIAL SCAN script or PLEX UPDATE script (Docker)
# When the show script is finished symlinking, it will trigger this script
# on_library_update: sh plex_update.sh "$@"

# dockerip=$(/sbin/ip route|awk '/default/ { print $3 }') # if zurg is running inside a Docker container
localip="127.0.0.1" # if the script is running on the host machine, and Plex is running on the same machine
external="plexdomain.com" # if Plex is running on a different machine

plexip=$localip # replace with your Plex IP

plex_url="http://$plexip:32400"
echo "Detected Plex URL inside Docker container: $plex_url"
token="yourplextoken" # open Plex in a browser, open dev console and copy-paste this: window.localStorage.getItem("myPlexAccessToken")
shows_dir="/path/to/your/showsdir" # replace with your RD shows directory path, ensure this is what Plex sees

# Get the library sections
sections=$(curl -s "$plex_url/library/sections?X-Plex-Token=$token")

# Extract the section ID for the Shows directory
section_id=$(echo "$sections" | xmllint --xpath "string(//Directory[./Location/@path='$shows_dir']/@key)" -)

if [ -z "$section_id" ]; then
    echo "Error: Could not find section ID for directory $shows_dir"
    exit 1
fi

# Get the location ID
location_id=$(echo "$sections" | xmllint --xpath "string(//Directory[@key='$section_id']/Location[@path='$shows_dir']/@id)" -)

if [ -z "$location_id" ]; then
    echo "Error: Could not find location ID for directory $shows_dir"
    exit 1
fi

echo "Updating in Plex: Section $section_id, Location $location_id"

encoded_path=$(echo -n "$shows_dir/$@" | python3 -c "import sys, urllib.parse as ul; print(ul.quote_plus(sys.stdin.read()))")

if [ -z "$encoded_path" ]; then
    echo "Error: encoded argument is empty, check the input or encoding process"
    exit 1
fi

final_url="${plex_url}/library/sections/${section_id}/refresh?location=${location_id}&path=${encoded_path}&X-Plex-Token=${token}"
curl -s "$final_url"
echo "Triggered scan with URL: $final_url"

echo "Section $section_id, Location $location_id refreshed!"

# credits to godver3, yowmamasita