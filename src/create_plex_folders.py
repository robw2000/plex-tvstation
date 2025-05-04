#!/usr/bin/env python3

"""
Script to create Plex media folders based on wishlist files.

This script reads movie and TV show names from wishlist files and creates properly 
formatted folders in the Plex media directories. It uses the OMDB API to look up 
metadata like release years and exact titles.

The empty folders created by this script allow plex_library_report.py to include
wishlist items in the missing episodes report, helping track what content still 
needs to be acquired.

Key features:
- Creates movie folders in format "Movie Title (Year)" 
- Creates TV show folders in format "Show Title Year-EndYear"
- Handles exact title matching and fuzzy matching
- Avoids creating duplicate folders
- Debug mode to preview folder creation
- Rate limiting for API calls

Required environment variables:
- omdb_api_key: API key for OMDB API access
- omdb_api_url: Base URL for OMDB API

Required files:
- movie_wishlist.txt: List of movies to create folders for
- tv_wishlist.txt: List of TV shows to create folders for
"""

import os
import re
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv
import time
import difflib
import argparse

# Load environment variables
load_dotenv()

# Constants
TV_SHOWS_PATH = Path("/mnt/g/plex/TV Shows")
MOVIES_PATH = Path("/mnt/g/plex/Movies")
OMDB_API_KEY = os.getenv("omdb_api_key")
OMDB_API_URL = os.getenv("omdb_api_url")
MOVIE_WISHLIST_FILE = "movie_wishlist.txt"
TV_WISHLIST_FILE = "tv_wishlist.txt"

def normalize_title(title: str) -> str:
	"""Normalize a title by removing non-alphanumeric characters and converting to lowercase"""
	# Convert to lowercase first
	title = title.lower()
	
	# Replace hyphens and apostrophes with spaces to preserve word boundaries
	title = title.replace('-', ' ').replace("'", ' ')
	
	# Remove all other non-alphanumeric characters
	normalized = re.sub(r'[^a-z0-9\s]', '', title)
	
	# Replace multiple spaces with a single space
	normalized = re.sub(r'\s+', ' ', normalized)
	
	# Trim leading/trailing spaces
	return normalized.strip()

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
	
	# Display all search results
	print("\nSearch results:")
	for i, result in enumerate(search_results["Search"], 1):
		print(f"{i}. {result['Title']} ({result.get('Year', 'N/A')})")
	print()
	
	# Normalize the input title
	normalized_input = normalize_title(clean_show_name)
	
	# Try to find an exact match first (ignoring non-alphanumeric characters and case)
	exact_matches = [result for result in search_results["Search"] 
	                 if normalize_title(result["Title"]) == normalized_input]
	
	if exact_matches:
		# Use the exact match
		exact_title = exact_matches[0]["Title"]
		print(f"Found exact title match: '{exact_title}'")
	else:
		# Use difflib to find the closest match
		choices = [result["Title"] for result in search_results["Search"]]
		closest_match = difflib.get_close_matches(clean_show_name, choices, n=1, cutoff=0.6)
		
		if closest_match:
			exact_title = closest_match[0]
			print(f"Found closest title match using difflib: '{exact_title}'")
		else:
			# Fall back to the first result if no good match found
			exact_title = search_results["Search"][0]["Title"]
			print(f"Found closest title match: '{exact_title}'")
	
	# Now get the show info using the exact title
	params = {
		"apikey": OMDB_API_KEY,
		"t": exact_title,
		"type": "series"
	}
	response = requests.get(OMDB_API_URL, params=params)
	return response.json()

def get_movie_info(movie_name: str) -> dict:
	"""Get movie information from OMDB API"""
	# Strip years from movie name (e.g., "Movie Name 2006" -> "Movie Name")
	clean_movie_name = re.sub(r'\s+\d{4}(-\d{4})?(-\s*)?$', '', movie_name)
	
	# First search for the movie to get the exact title
	search_params = {
		"apikey": OMDB_API_KEY,
		"s": clean_movie_name,
		"type": "movie"
	}
	search_response = requests.get(OMDB_API_URL, params=search_params)
	search_results = search_response.json()
	
	print(f"Search results for '{clean_movie_name}': {search_results.get('Response', 'Unknown')}")
	
	if search_results.get("Response") == "False" or "Error" in search_results:
		return search_results
		
	if not search_results.get("Search"):
		return {"Response": "False", "Error": "No results found"}
	
	# Display all search results
	print("\nSearch results:")
	for i, result in enumerate(search_results["Search"], 1):
		print(f"{i}. {result['Title']} ({result.get('Year', 'N/A')})")
	print()
	
	# Normalize the input title
	normalized_input = normalize_title(clean_movie_name)
	
	# Try to find an exact match first (ignoring non-alphanumeric characters and case)
	exact_matches = [result for result in search_results["Search"] 
					if normalize_title(result["Title"]) == normalized_input]
	
	if exact_matches:
		# Use the exact match
		exact_title = exact_matches[0]["Title"]
		print(f"Found exact title match: '{exact_title}'")
	else:
		# Use difflib to find the closest match, but with a higher cutoff to avoid matching with sequels
		choices = [result["Title"] for result in search_results["Search"]]
		closest_match = difflib.get_close_matches(clean_movie_name, choices, n=1, cutoff=0.8)
		
		if closest_match:
			# Additional check to prevent matching with sequels or alternate cuts
			matched_title = closest_match[0]
			normalized_matched = normalize_title(matched_title)
			normalized_input_words = set(normalized_input.split())
			normalized_matched_words = set(normalized_matched.split())
			
			# Check if the matched title contains additional words that aren't in the input
			extra_words = normalized_matched_words - normalized_input_words
			if extra_words and any(word.isdigit() for word in extra_words):
				# If there are extra words and they contain numbers (like "2" or "3"), don't use this match
				print(f"Rejecting match '{matched_title}' as it appears to be a sequel or alternate cut")
				# Try to find a match without sequel numbers
				non_sequel_matches = [title for title in choices 
									if not any(word.isdigit() for word in set(normalize_title(title).split()) - normalized_input_words)]
				if non_sequel_matches:
					exact_title = non_sequel_matches[0]
					print(f"Found non-sequel match: '{exact_title}'")
				else:
					# Fall back to the first result if no good match found
					exact_title = search_results["Search"][0]["Title"]
					print(f"Found closest title match: '{exact_title}'")
			else:
				exact_title = matched_title
				print(f"Found closest title match using difflib: '{exact_title}'")
		else:
			# Fall back to the first result if no good match found
			exact_title = search_results["Search"][0]["Title"]
			print(f"Found closest title match: '{exact_title}'")
	
	# Now get the movie info using the exact title
	params = {
		"apikey": OMDB_API_KEY,
		"t": exact_title,
		"type": "movie"
	}
	response = requests.get(OMDB_API_URL, params=params)
	return response.json()

def create_tv_show_folder(show_name: str, debug: bool = False) -> tuple:
	"""Create a TV show folder in the Plex TV Shows directory or return the folder path if in debug mode"""
	# Get show info from OMDB
	show_info = get_show_info(show_name)
	
	if show_info.get("Response") == "False" or "Error" in show_info:
		print(f"Error: Could not find TV show '{show_name}': {show_info.get('Error', 'Unknown error')}")
		return None, False
		
	# Extract show title and years
	show_title = show_info.get("Title", show_name)
	start_year = show_info.get("Year", "")
	end_year = show_info.get("EndYear", "")
	
	# Format folder name
	if end_year and end_year != "N/A":
		folder_name = f"{show_title} {start_year}-{end_year}"
	else:
		folder_name = f"{show_title} {start_year}"
		
	# Create folder path
	folder_path = TV_SHOWS_PATH / folder_name
	
	# Check if folder already exists
	if folder_path.exists():
		print(f"TV show folder already exists: {folder_path}")
		return folder_path, True
		
	# Create folder or just return the path in debug mode
	if debug:
		print(f"[DEBUG] Would create TV show folder: {folder_path}")
		return folder_path, True
	else:
		try:
			folder_path.mkdir(parents=True, exist_ok=True)
			print(f"Created TV show folder: {folder_path}")
			return folder_path, True
		except Exception as e:
			print(f"Error creating TV show folder: {e}")
			return folder_path, False

def create_movie_folder(movie_name: str, debug: bool = False) -> tuple:
	"""Create a movie folder in the Plex Movies directory or return the folder path if in debug mode"""
	# Get movie info from OMDB
	movie_info = get_movie_info(movie_name)
	
	if movie_info.get("Response") == "False" or "Error" in movie_info:
		print(f"Error: Could not find movie '{movie_name}': {movie_info.get('Error', 'Unknown error')}")
		return None, False
		
	# Extract movie title and year
	movie_title = movie_info.get("Title", movie_name)
	year = movie_info.get("Year", "")
	
	# Format folder name
	folder_name = f"{movie_title} {year}"
		
	# Create folder path
	folder_path = MOVIES_PATH / folder_name
	
	# Check if folder already exists
	if folder_path.exists():
		print(f"Movie folder already exists: {folder_path}")
		return folder_path, True
		
	# Create folder or just return the path in debug mode
	if debug:
		print(f"[DEBUG] Would create movie folder: {folder_path}")
		return folder_path, True
	else:
		try:
			folder_path.mkdir(parents=True, exist_ok=True)
			print(f"Created movie folder: {folder_path}")
			return folder_path, True
		except Exception as e:
			print(f"Error creating movie folder: {e}")
			return folder_path, False

def process_wishlist_files(file_location, debug: bool = False) -> tuple:
	"""Process the movie and TV show wishlist files"""
	movie_folders = []
	tv_folders = []
	
	# Process movie wishlist
	if os.path.exists(file_location / MOVIE_WISHLIST_FILE):
		print(f"\nProcessing movie wishlist from '{MOVIE_WISHLIST_FILE}'...")
		with open(file_location / MOVIE_WISHLIST_FILE, 'r') as f:
			movie_items = [line.strip() for line in f if line.strip()]
			
		if not movie_items:
			print(f"Warning: '{MOVIE_WISHLIST_FILE}' is empty.")
		else:
			print(f"Found {len(movie_items)} movies to process.")
			
			for movie_name in movie_items:
				print(f"\nProcessing movie: {movie_name}")
				folder_path, success = create_movie_folder(movie_name, debug)
				if success and folder_path:
					movie_folders.append(folder_path)
				# Add a small delay to avoid hitting API rate limits
				time.sleep(1)
	else:
		print(f"Warning: Movie wishlist file '{MOVIE_WISHLIST_FILE}' not found.")
	
	# Process TV show wishlist
	if os.path.exists(file_location / TV_WISHLIST_FILE):
		print(f"\nProcessing TV show wishlist from '{TV_WISHLIST_FILE}'...")
		with open(file_location / TV_WISHLIST_FILE, 'r') as f:
			tv_items = [line.strip() for line in f if line.strip()]
			
		if not tv_items:
			print(f"Warning: '{TV_WISHLIST_FILE}' is empty.")
		else:
			print(f"Found {len(tv_items)} TV shows to process.")
			
			for show_name in tv_items:
				print(f"\nProcessing TV show: {show_name}")
				folder_path, success = create_tv_show_folder(show_name, debug)
				if success and folder_path:
					tv_folders.append(folder_path)
				# Add a small delay to avoid hitting API rate limits
				time.sleep(1)
	else:
		print(f"Warning: TV show wishlist file '{TV_WISHLIST_FILE}' not found.")
		
	return movie_folders, tv_folders

def run_create_plex_folders(args, file_location):
	# Adjust paths to use file_location
	logs_dir = file_location / 'logs'
	logs_dir.mkdir(exist_ok=True)
	
	# Check if OMDB API key is available
	if not OMDB_API_KEY:
		print("Error: OMDB API key not found. Please set the 'omdb_api_key' environment variable.")
		return
		
	# Process the wishlist files
	movie_folders, tv_folders = process_wishlist_files(file_location, args.debug)
	
	# Print summary
	print("\n" + "="*50)
	print("SUMMARY")
	print("="*50)
	
	if args.debug:
		print("\n[DEBUG MODE] The following folders would have been created:")
	else:
		print("\nThe following folders were created:")
		
	print("\nMovie Folders:")
	if movie_folders:
		for folder in movie_folders:
			print(f"  - {folder}")
	else:
		print("  None")
		
	print("\nTV Show Folders:")
	if tv_folders:
		for folder in tv_folders:
			print(f"  - {folder}")
	else:
		print("  None")
		
	print("\nProcessing complete!")
