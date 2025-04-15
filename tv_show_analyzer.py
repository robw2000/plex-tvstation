#!/usr/bin/env python3

import os
import re
from pathlib import Path
import requests
from dotenv import load_dotenv
from tabulate import tabulate
from typing import Dict, List, Set, Tuple

# Load environment variables
load_dotenv()

# Constants
TV_SHOWS_PATH = Path("/mnt/g/plex/TV Shows")
OMDB_API_KEY = os.getenv("omdb_api_key")
OMDB_API_URL = os.getenv("omdb_api_url")

def get_show_info(show_name: str) -> dict:
	"""Get show information from OMDB API"""
	# Strip years from show name (e.g., "Show Name 2006-2013" or "Show Name 2006-" -> "Show Name")
	clean_show_name = re.sub(r'\s+\d{4}(-\d{4})?(-\s*)?$', '', show_name)
	
	# First search for the show to get the exact title
	search_params = {
		"apikey": OMDB_API_KEY,
		"s": clean_show_name,
		"type": "series"
	}
	search_response = requests.get(OMDB_API_URL, params=search_params)
	search_results = search_response.json()
	
	print(f"Search results for '{clean_show_name}': {search_results.get('Response', 'Unknown')}")
	
	if search_results.get("Response") == "False" or "Error" in search_results:
		return search_results
		
	if not search_results.get("Search"):
		return {"Response": "False", "Error": "No results found"}
		
	# Get the first result's exact title
	exact_title = search_results["Search"][0]["Title"]
	print(f"Found exact title: '{exact_title}'")
	
	# Now get the show info using the exact title
	params = {
		"apikey": OMDB_API_KEY,
		"t": exact_title,
		"type": "series"
	}
	response = requests.get(OMDB_API_URL, params=params)
	return response.json()

def get_episode_info(show_name: str, season: int) -> dict:
	"""Get episode information for a specific season from OMDB API"""
	# Strip years from show name (e.g., "Show Name 2006-2013" or "Show Name 2006-" -> "Show Name")
	clean_show_name = re.sub(r'\s+\d{4}(-\d{4})?(-\s*)?$', '', show_name)
	
	# First search for the show to get the exact title
	search_params = {
		"apikey": OMDB_API_KEY,
		"s": clean_show_name,
		"type": "series"
	}
	search_response = requests.get(OMDB_API_URL, params=search_params)
	search_results = search_response.json()
	
	if search_results.get("Response") == "False" or "Error" in search_results:
		return search_results
		
	if not search_results.get("Search"):
		return {"Response": "False", "Error": "No results found"}
		
	# Get the first result's exact title
	exact_title = search_results["Search"][0]["Title"]
	
	# Now get the episode info using the exact title
	params = {
		"apikey": OMDB_API_KEY,
		"t": exact_title,
		"type": "series",
		"Season": season
	}
	response = requests.get(OMDB_API_URL, params=params)
	return response.json()

def analyze_local_shows() -> Dict[str, Dict[int, Set[str]]]:
	"""Analyze local TV show folders and return show/season/episode structure"""
	local_shows = {}
	
	print(f"Looking for TV shows in: {TV_SHOWS_PATH}")
	
	for show_path in TV_SHOWS_PATH.iterdir():
		if not show_path.is_dir():
			continue
			
		show_name = show_path.name
		print(f"Found show: {show_name}")
		local_shows[show_name] = {}
		
		for season_path in show_path.iterdir():
			if not season_path.is_dir():
				continue
				
			# Extract season number from folder name
			match = re.match(r"Season (\d+)", season_path.name)
			if not match:
				continue
				
			season_num = int(match.group(1))
			episodes = set()
			
			for episode_file in season_path.glob("*.mkv"):
				episodes.add(episode_file.stem)
				
			local_shows[show_name][season_num] = episodes
			print(f"  Season {season_num}: {len(episodes)} episodes")
			
	return local_shows

def analyze_show(show_name: str, local_data: Dict[int, Set[str]]) -> List[Tuple[str, str, str]]:
	"""Compare local show data with OMDB data and return missing episodes"""
	missing_items = []
	
	# Get show info from OMDB
	show_info = get_show_info(show_name)
	print(f"OMDB search for '{show_name}' returned: {show_info.get('Response', 'Unknown')}")
	
	if "Error" in show_info:
		missing_items.append((show_name, "Error", f"Could not find show: {show_info['Error']}"))
		return missing_items
		
	if show_info.get("Response") == "False":
		missing_items.append((show_name, "Error", f"Could not find show: {show_info.get('Error', 'Unknown error')}"))
		return missing_items
		
	total_seasons = int(show_info.get("totalSeasons", 0))
	print(f"  Total seasons according to OMDB: {total_seasons}")
	
	# Check for missing seasons
	for season in range(1, total_seasons + 1):
		if season not in local_data:
			missing_items.append((show_name, f"Season {season:02d}", "Entire season missing"))
			continue
			
		# Get episode info for this season
		episode_info = get_episode_info(show_name, season)
		print(f"  Season {season} info: {episode_info.get('Response', 'Unknown')}")
		
		if "Error" in episode_info:
			missing_items.append((show_name, f"Season {season:02d}", f"Could not get episode info: {episode_info['Error']}"))
			continue
			
		if episode_info.get("Response") == "False":
			missing_items.append((show_name, f"Season {season:02d}", f"Could not get episode info: {episode_info.get('Error', 'Unknown error')}"))
			continue
			
		# Check for missing episodes
		local_episodes = local_data[season]
		print(f"  Local episodes in season {season}: {len(local_episodes)}")
		print(f"  OMDB episodes in season {season}: {len(episode_info.get('Episodes', []))}")
		
		for episode in episode_info.get("Episodes", []):
			episode_num = int(episode["Episode"])
			episode_name = f"E{episode_num:02d} - {episode['Title']}"
			
			if not any(episode_name.startswith(f"E{episode_num:02d}") for ep in local_episodes):
				missing_items.append((show_name, f"Season {season:02d}", episode_name))
				
	return missing_items

def main():
	# Analyze local shows
	print("Analyzing local TV shows...")
	local_shows = analyze_local_shows()
	
	# Compare with OMDB data
	print("Comparing with OMDB data...")
	all_missing_items = []
	
	for show_name, seasons in local_shows.items():
		print(f"Analyzing {show_name}...")
		missing_items = analyze_show(show_name, seasons)
		all_missing_items.extend(missing_items)
		
	# Create markdown report
	headers = ["Show", "Season", "Missing Item"]
	markdown_table = tabulate(all_missing_items, headers=headers, tablefmt="pipe")
	
	# Write to file
	with open("missing_episodes.md", "w") as f:
		f.write("# Missing TV Show Episodes\n\n")
		f.write(markdown_table)
		
	print("\nAnalysis complete! Results written to missing_episodes.md")

if __name__ == "__main__":
	main() 