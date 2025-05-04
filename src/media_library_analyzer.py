#!/usr/bin/env python3

"""
Media Library Analyzer

This script analyzes your local media library and compares it with online databases to identify missing episodes and movies.
It scans your TV show and movie directories, compares the content with OMDB database information, and generates a detailed
report of missing episodes and movies.

Features:
- Scans local TV show and movie directories
- Compares local content with OMDB database to identify missing episodes
- Generates a detailed markdown report of missing content
- Provides a summary of missing episodes and movies
- Helps identify incomplete TV show seasons and missing movies

Requirements:
- Python 3.x
- Required Python packages:
  - requests
  - python-dotenv
  - tabulate

Setup:
- Fill the variables in the .env file or set them as environment variables:
  - tv_shows_path: Path to your TV shows directory
  - movies_path: Path to your movies directory
  - omdb_api_key: Your OMDB API key
  - omdb_api_url: The OMDB API URL (defaults to http://www.omdbapi.com/)

Usage:
- Run the script: python media_library_analyzer.py
- The script will generate a markdown report in the logs directory
- The report will include a table of all missing episodes and movies
- A summary section will be included with information about missing seasons and individual episodes
"""

import os
import re
from pathlib import Path
import requests
from dotenv import load_dotenv
from tabulate import tabulate
from typing import Dict, List, Set, Tuple
import datetime
import glob
import time
import argparse

# Load environment variables
load_dotenv()

# Global variables
log_only = False

# Constants
TV_SHOWS_PATH = Path("/mnt/g/plex/TV Shows")
MOVIES_PATH = Path("/mnt/g/plex/Movies")
OMDB_API_KEY = os.getenv("omdb_api_key")
OMDB_API_URL = os.getenv("omdb_api_url")

# Get script directory for file operations
SCRIPT_DIR = Path(__file__).parent.absolute()
LOGS_DIR = SCRIPT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def get_show_info(show_name: str) -> dict:
	"""
	Get show information from OMDB API.
	
	This function queries the OMDB API to get detailed information about a TV show.
	It first searches for the show to get the exact title, then retrieves the full show information.
	
	Args:
		show_name: The name of the show to search for
		
	Returns:
		A dictionary containing the show information from OMDB API
	"""
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
	
	print_message(f"Search results for '{clean_show_name}': {search_results.get('Response', 'Unknown')}")
	
	if search_results.get("Response") == "False" or "Error" in search_results:
		return search_results
		
	if not search_results.get("Search"):
		return {"Response": "False", "Error": "No results found"}
		
	# Get the first result's exact title
	exact_title = search_results["Search"][0]["Title"]
	print_message(f"Found exact title: '{exact_title}'")
	
	# Now get the show info using the exact title
	params = {
		"apikey": OMDB_API_KEY,
		"t": exact_title,
		"type": "series"
	}
	response = requests.get(OMDB_API_URL, params=params)
	return response.json()

def get_episode_info(show_name: str, season: int) -> dict:
	"""
	Get episode information for a specific season from OMDB API.
	
	This function queries the OMDB API to get detailed information about all episodes
	in a specific season of a TV show.
	
	Args:
		show_name: The name of the show
		season: The season number to get information for
		
	Returns:
		A dictionary containing the episode information from OMDB API
	"""
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
	"""
	Analyze local TV show folders and return show/season/episode structure.
	
	This function scans the local TV show directory and builds a dictionary
	representing the structure of shows, seasons, and episodes.
	
	Returns:
		A dictionary with show names as keys and nested dictionaries as values.
		The nested dictionaries have season numbers as keys and sets of episode filenames as values.
	"""
	local_shows = {}
	
	print_message(f"Looking for TV shows in: {TV_SHOWS_PATH}")
	
	for show_path in TV_SHOWS_PATH.iterdir():
		if not show_path.is_dir():
			continue
			
		show_name = show_path.name
		print_message(f"Found show: {show_name}")
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
			print_message(f"  Season {season_num}: {len(episodes)} episodes")
			
	return local_shows

def analyze_show(show_name: str, local_data: Dict[int, Set[str]]) -> List[Tuple[str, str, str]]:
	"""
	Compare local show data with OMDB data and return missing episodes.
	
	This function compares the local TV show data with information from the OMDB API
	to identify missing episodes and seasons.
	
	Args:
		show_name: The name of the show to analyze
		local_data: A dictionary with season numbers as keys and sets of episode filenames as values
		
	Returns:
		A list of tuples containing (show_name, season, missing_item) for each missing episode or season
	"""
	missing_items = []
	
	# Get show info from OMDB
	show_info = get_show_info(show_name)
	print_message(f"OMDB search for '{show_name}' returned: {show_info.get('Response', 'Unknown')}")
	
	if "Error" in show_info:
		missing_items.append((show_name, "Error", f"Could not find show: {show_info['Error']}"))
		return missing_items
		
	if show_info.get("Response") == "False":
		missing_items.append((show_name, "Error", f"Could not find show: {show_info.get('Error', 'Unknown error')}"))
		return missing_items
		
	total_seasons = int(show_info.get("totalSeasons", 0))
	print_message(f"  Total seasons according to OMDB: {total_seasons}")
	
	# Check for missing seasons
	for season in range(1, total_seasons + 1):
		if season not in local_data:
			missing_items.append((show_name, f"Season {season:02d}", "Entire season missing"))
			continue
			
		# Get episode info for this season
		episode_info = get_episode_info(show_name, season)
		print_message(f"  Season {season} info: {episode_info.get('Response', 'Unknown')}")
		
		if "Error" in episode_info:
			missing_items.append((show_name, f"Season {season:02d}", f"Could not get episode info: {episode_info['Error']}"))
			continue
			
		if episode_info.get("Response") == "False":
			missing_items.append((show_name, f"Season {season:02d}", f"Could not get episode info: {episode_info.get('Error', 'Unknown error')}"))
			continue
			
		# Check for missing episodes
		local_episodes = local_data[season]
		print_message(f"  Local episodes in season {season}: {len(local_episodes)}")
		print_message(f"  OMDB episodes in season {season}: {len(episode_info.get('Episodes', []))}")
		
		# Create a mapping of episode numbers to their filenames
		local_episode_map = {}
		for ep in local_episodes:
			# Try to extract episode number from filename using multiple patterns
			# Pattern 1: "E01" format
			match = re.match(r"E(\d+)", ep)
			if match:
				ep_num = int(match.group(1))
				local_episode_map[ep_num] = ep
				continue
				
			# Pattern 2: "s01e01" format
			match = re.search(r"s\d+e(\d+)", ep.lower())
			if match:
				ep_num = int(match.group(1))
				local_episode_map[ep_num] = ep
				continue
				
			# Pattern 3: Just look for any number after "e" or "E"
			match = re.search(r"[eE](\d+)", ep)
			if match:
				ep_num = int(match.group(1))
				local_episode_map[ep_num] = ep
		
		for episode in episode_info.get("Episodes", []):
			episode_num = int(episode["Episode"])
			episode_name = f"E{episode_num:02d} - {episode['Title']}"
			
			# Check if we have this episode number in our local files
			if episode_num not in local_episode_map:
				missing_items.append((show_name, f"Season {season:02d}", episode_name))
				
	return missing_items

def analyze_local_movies() -> List[Tuple[str, str, str]]:
	"""
	Analyze local movie folders and return list of empty or invalid folders.
	
	This function scans the local movie directory and identifies folders that are
	empty or don't contain any MKV files.
	
	Returns:
		A list of tuples containing (movie_name, "Movie", issue_description) for each problematic movie folder
	"""
	missing_items = []
	
	print_message(f"Looking for movies in: {MOVIES_PATH}")
	
	for movie_path in MOVIES_PATH.iterdir():
		if not movie_path.is_dir():
			continue
			
		movie_name = movie_path.name
		print_message(f"Found movie: {movie_name}")
		
		# Check if folder is empty
		if not any(movie_path.iterdir()):
			missing_items.append((movie_name, "Movie", "Empty folder"))
			continue
			
		# Check if folder only contains non-MKV files
		has_mkv = False
		for file in movie_path.iterdir():
			if file.suffix.lower() == '.mkv':
				has_mkv = True
				break
				
		if not has_mkv:
			missing_items.append((movie_name, "Movie", "No MKV files found"))
			
	return missing_items

def print_message(message):
	if log_only:
		return
	print(message)

def log_cron_message(script_name, args=None):
	"""
	Log a basic message to cron.log with script name and arguments.
	This is used for cron job logging.
	"""
	timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
	cron_log = LOGS_DIR / "cron.log"
	
	# Only include non-None arguments that were actually passed
	args_str = ' '.join(f"{k}={v}" for k, v in args.items() if v is not None) if args else ''
	message = f"[{timestamp}] Running {script_name} with args: {args_str}"
	
	with open(cron_log, 'a') as f:
		f.write(f"{message}\n")

def run_media_library_analyzer(args):
	"""
	Main function that orchestrates the media library analysis.
	
	Arguments:
		--log-only, -l: If specified, only log the script execution without performing analysis
	"""
	
	# Set global log_only variable
	global log_only
	log_only = args.log_only
	
	# Log script execution to cron.log
	log_cron_message("media_library_analyzer.py", vars(args))
	
	# Analyze local shows
	print_message("Analyzing local TV shows...")
	local_shows = analyze_local_shows()
	
	# Compare with OMDB data
	print_message("Comparing with OMDB data...")
	all_missing_items = []
	
	for show_name, seasons in local_shows.items():
		print_message(f"Analyzing {show_name}...")
		missing_items = analyze_show(show_name, seasons)
		all_missing_items.extend(missing_items)
		
	# Analyze local movies
	print_message("\nAnalyzing local movies...")
	movie_missing_items = analyze_local_movies()
	all_missing_items.extend(movie_missing_items)
		
	# Create markdown report
	headers = ["Show", "Season", "Missing Item"]
	markdown_table = tabulate(all_missing_items, headers=headers, tablefmt="pipe")
	
	# Generate summary section
	show_summary = {}
	for show, season, item in all_missing_items:
		if show not in show_summary:
			show_summary[show] = {}
		
		if season == "Error":
			continue
			
		if season == "Movie":
			if "Movie" not in show_summary[show]:
				show_summary[show]["Movie"] = []
			show_summary[show]["Movie"].append(item)
			continue
			
		season_num = int(season.split()[1])
		if season_num not in show_summary[show]:
			show_summary[show][season_num] = []
			
		if item == "Entire season missing":
			show_summary[show][season_num] = ["Entire season missing"]
		else:
			show_summary[show][season_num].append(item)
	
	# Format summary as markdown
	summary_lines = ["\n## Summary of Missing Content\n"]
	
	# Create separate lists for shows with missing episodes and movies
	shows_with_missing_episodes = []
	shows_with_missing_movies = []
	
	for show in sorted(show_summary.keys()):
		episode_summary = []
		movie_summary = []
		
		# Handle movies first
		if "Movie" in show_summary[show]:
			movie_summary.append(f"{', '.join(show_summary[show]['Movie'])}")
			
		# Then handle TV show seasons
		for season_num in sorted(show_summary[show].keys()):
			if season_num == "Movie":
				continue
				
			items = show_summary[show][season_num]
			if items == ["Entire season missing"]:
				episode_summary.append(f"Season {season_num}")
			else:
				episode_nums = []
				for item in items:
					match = re.match(r"E(\d+)", item)
					if match:
						episode_nums.append(int(match.group(1)))
				
				if episode_nums:
					# Get the total number of episodes in this season from OMDB
					episode_info = get_episode_info(show, season_num)
					total_episodes = len(episode_info.get("Episodes", [])) if episode_info.get("Response") == "True" else 0
					
					# If we have no episode info or all episodes are missing
					if total_episodes == 0 or len(episode_nums) >= total_episodes:
						episode_summary.append(f"Season {season_num}")
					# If more than half of the episodes are missing
					elif len(episode_nums) > total_episodes / 2:
						episode_summary.append(f"Season {season_num} (most episodes missing)")
					else:
						if len(episode_nums) == 1:
							episode_summary.append(f"Season {season_num} missing episode {episode_nums[0]}")
						else:
							episode_summary.append(f"Season {season_num} missing episodes {', '.join(map(str, sorted(episode_nums)))}")
		
		if episode_summary:
			shows_with_missing_episodes.append(f"* `{show}` - {'; '.join(episode_summary)}")
		
		if movie_summary:
			shows_with_missing_movies.append(f"* `{show}` - {'; '.join(movie_summary)}")
	
	# Add the sections to the summary
	if shows_with_missing_episodes:
		summary_lines.append("\n### Missing Episodes")
		summary_lines.extend(shows_with_missing_episodes)
	
	if shows_with_missing_movies:
		summary_lines.append("\n### Missing Movies")
		summary_lines.extend(shows_with_missing_movies)
	
	# Use a fixed filename that will be overwritten each time
	output_file = LOGS_DIR / "missing_episodes.md"
	
	# Write to file
	with open(output_file, "w") as f:
		f.write("# Missing TV Show Episodes and Movies\n\n")
		f.write(markdown_table)
		f.write("\n".join(summary_lines))
		f.write(f"\n\n---\nLast updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
	
	print_message(f"\nAnalysis complete! Results written to {output_file}")

