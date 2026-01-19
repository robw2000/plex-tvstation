#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
This script generates a detailed report of your Plex library, including:
- Total number of movies and TV shows
- Breakdown of watched vs unwatched content
- List of TV shows with episode counts
- List of movies with their years
- Storage usage statistics
"""

from os import getenv, path, makedirs, walk, stat
import os
from pathlib import Path
import re
import time
import datetime
import requests

from media_library_analyzer import PLEX_GLOBALS
from utils import build_genres_set, test_plex_connectivity_with_fallback

def initialize_plex_globals(file_location):
	"""
	Initialize the PLEX_GLOBALS dictionary with environment variables and other global settings.
	"""

	# Ensure plex_movies_folder and plex_tv_folder are set
	plex_movies_folder = getenv('plex_movies_folder')
	plex_tv_folder = getenv('plex_tv_folder')
	if not plex_movies_folder:
		log_message("Error: plex_movies_folder environment variable is not set.")
		raise EnvironmentError("plex_movies_folder environment variable is not set.")
	if not plex_tv_folder:
		log_message("Error: plex_tv_folder environment variable is not set.")
		raise EnvironmentError("plex_tv_folder environment variable is not set.")

	# Adjust paths to use file_location
	logs_dir = file_location / 'logs'
	logs_dir.mkdir(exist_ok=True)

	plex_globals = {
		'plex_ip': getenv('plex_ip', '192.168.1.196'),
		'plex_port': getenv('plex_port', '32400'),
		'plex_api_token': getenv('plex_api_token', ''),
		'user_id': getenv('user_id', '1'),
		'base_url': None,
		'movies_section_key': None,
		'tv_section_key': None,
		'MOVIES_PATH': Path(plex_movies_folder),
		'TV_SHOWS_PATH': Path(plex_tv_folder),
		'logs_dir': logs_dir,
		'log_file': path.join(logs_dir, 'plex_library_report.log'),
		'markdown_file': path.join(logs_dir, 'library-media.md')
	}

	return plex_globals

def log_message(*args, **kwargs):
	"""
	Log a message to both the log file and stdout.
	This function takes the same arguments as the print function.
	"""
	# Format the message
	message = ' '.join(str(arg) for arg in args)
	
	# Print to stdout
	print(*args, **kwargs)
	
	# Write to log file
	with open(PLEX_GLOBALS['log_file'], 'a') as f:
		f.write(f"{message}\n")

def write_markdown(*args, **kwargs):
	"""
	Write a message to the markdown file.
	ThiPLEX_GLOBALSakes the same arguments as the print function.
	"""
	# Format the message
	message = ' '.join(str(arg) for arg in args)
	
	# Write to markdown file
	with open(PLEX_GLOBALS['markdown_file'], 'a') as f:
		f.write(f"{message}\n")

def clear_log():
	"""
	Clear the log file if it exists.
	"""
	if path.exists(PLEX_GLOBALS['log_file']):
		os.remove(PLEX_GLOBALS['log_file'])

def clear_markdown():
	"""
	Clear the markdown file and add the header.
	"""
	with open(PLEX_GLOBALS['markdown_file'], 'w') as f:
		f.write("# Plex Library Report\n\n")
		f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

def get_base_url():
	"""
	Retrieves the base URL for the Plex server.
	"""
	# Always rebuild base_url from current IP to handle IP changes
	PLEX_GLOBALS['base_url'] = f"http://{PLEX_GLOBALS['plex_ip']}:{PLEX_GLOBALS['plex_port']}"
	return PLEX_GLOBALS['base_url']

def get_section_keys(ssn):
	"""
	Retrieves the section keys for Movies and TV Shows from the Plex server.
	"""
	if PLEX_GLOBALS['movies_section_key'] is not None and PLEX_GLOBALS['tv_section_key'] is not None:
		return PLEX_GLOBALS['movies_section_key'], PLEX_GLOBALS['tv_section_key']
	
	base_url = get_base_url()
	sections = ssn.get(f'{base_url}/library/sections/').json()['MediaContainer']['Directory']
	for section in sections:
		if section['title'] == 'Movies':
			PLEX_GLOBALS['movies_section_key'] = section['key']
		if section['title'] == 'TV Shows':
			PLEX_GLOBALS['tv_section_key'] = section['key']

	return PLEX_GLOBALS['movies_section_key'], PLEX_GLOBALS['tv_section_key']

def calculate_directory_size(directory, title=None, year=None):
	total_size = 0
	movies_path = PLEX_GLOBALS['MOVIES_PATH']
	tv_show_path = PLEX_GLOBALS['TV_SHOWS_PATH']

	for dirpath, dirnames, filenames in walk(directory):
		for d in dirnames:
			# Check if we're in the movies directory
			if str(movies_path) in str(directory) and title is not None and year is not None and d.startswith(title) and d.endswith(str(year)):
				dp = path.join(dirpath, d)
				return calculate_directory_size(dp)
			# Check if we're in the TV shows directory
			elif str(tv_show_path) in str(directory) and title is not None and d.startswith(title):
				dp = path.join(dirpath, d)
				return calculate_directory_size(dp)
			elif str(tv_show_path) in str(directory) and d.startswith('Season '):
				dp = path.join(dirpath, d)
				return calculate_directory_size(dp)

		for f in filenames:
			fp = path.join(dirpath, f)
			try:
				file_size = stat(fp).st_size
				total_size += file_size
				# print(f"File: {fp}, Size: {file_size}")  # Debugging output
			except FileNotFoundError:
				print(f"File not found: {fp}")  # Debugging output
	return total_size

def get_movie_stats(ssn):
	"""
	Retrieves statistics about movies in the library, including file sizes from disk.
	"""
	base_url = get_base_url()
	movie_section_key, _ = get_section_keys(ssn)
	
	results = ssn.get(f'{base_url}/library/sections/{movie_section_key}/all', params={})
	results.raise_for_status()
	results_json = results.json()
	movie_list = results_json['MediaContainer']['Metadata']
	
	total_movies = len(movie_list)
	watched_movies = len([m for m in movie_list if m.get('viewCount', 0) > 0])
	unwatched_movies = total_movies - watched_movies
	
	# Create a list of all movies with their details
	movies_list = []
	genre_counts = {}  # Track genre counts
	
	for movie in movie_list:
		# Calculate file size from disk
		movies_path = PLEX_GLOBALS['MOVIES_PATH']
		
		# print(f"Checking movie path {movies_path} for {movie['title']}")  # Debugging output
		file_size = calculate_directory_size(movies_path, movie['title'], movie['year'])

		# Track genres
		movie_genres = []
		for genre_name in build_genres_set(movie.get('Genre', [])):
			genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
			movie_genres.append(genre_name)
		
		movies_list.append({
			'title': movie['title'],
			'year': movie.get('year', 'Unknown'),
			'watched': movie.get('viewCount', 0) > 0,
			'file_size': format_size(file_size),
			'genres': movie_genres
		})
	
	return {
		'total': total_movies,
		'watched': watched_movies,
		'unwatched': unwatched_movies,
		'movies_list': sorted(movies_list, key=lambda x: (x['year'], x['title'])),
		'genre_counts': genre_counts
	}

def get_tv_stats(ssn):
	"""
	Retrieves statistics about TV shows in the library, including file sizes from disk.
	"""
	base_url = get_base_url()
	_, tv_section_key = get_section_keys(ssn)
	
	results = ssn.get(f'{base_url}/library/sections/{tv_section_key}/all', params={})
	results.raise_for_status()
	results_json = results.json()
	series_list = results_json['MediaContainer']['Metadata']
	
	total_shows = len(series_list)
	total_episodes = 0
	watched_episodes = 0
	
	# Get detailed stats for each show
	shows_stats = []
	genre_counts = {}  # Track genre counts
	
	for series in series_list:
		series_key = series['ratingKey']
		
		# Get detailed series info including genres
		series_details = ssn.get(f'{base_url}/library/metadata/{series_key}', params={}).json()['MediaContainer']['Metadata'][0]
		
		# Track genres
		series_genres = []
		for genre_name in build_genres_set(series_details.get('Genre', [])):
			genre_counts[genre_name] = genre_counts.get(genre_name, 0) + 1
			series_genres.append(genre_name)
		
		seasons = ssn.get(f'{base_url}/library/metadata/{series_key}/children', params={}).json()['MediaContainer']['Metadata']
		
		show_episodes = 0
		show_watched = 0
		show_size = 0
		
		for season in seasons:
			season_key = season['ratingKey']
			episodes = ssn.get(f'{base_url}/library/metadata/{season_key}/children', params={}).json()['MediaContainer']['Metadata']
			
			show_episodes += len(episodes)
			show_watched += len([e for e in episodes if e.get('viewCount', 0) > 0])
			
			# Calculate file size from disk for each episode
			for episode in episodes:
				tv_show_path = PLEX_GLOBALS['TV_SHOWS_PATH']
				show_size += calculate_directory_size(tv_show_path, series['title'])
		
		total_episodes += show_episodes
		watched_episodes += show_watched
		
		# Calculate average episode size
		avg_episode_size = show_size / show_episodes if show_episodes > 0 else 0
		
		shows_stats.append({
			'title': series['title'],
			'episodes': show_episodes,
			'watched': show_watched,
			'percent_watched': (show_watched / show_episodes * 100) if show_episodes > 0 else 0,
			'file_size': format_size(show_size),
			'avg_episode_size': format_size(avg_episode_size),
			'genres': series_genres  # Add cleaned genres to show stats
		})
	
	return {
		'total_shows': total_shows,
		'total_episodes': total_episodes,
		'watched_episodes': watched_episodes,
		'unwatched_episodes': total_episodes - watched_episodes,
		'shows_stats': shows_stats,
		'genre_counts': genre_counts
	}

def format_size(size_bytes):
	"""
	Format bytes into human readable format.
	"""
	for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
		if size_bytes < 1024.0:
			return f"{size_bytes:.2f} {unit}"
		size_bytes /= 1024.0
	return f"{size_bytes:.2f} PB"

def generate_report(ssn):
	"""
	Generates a comprehensive report of the Plex library, including file sizes.
	"""
	# Check if markdown file was updated less than a day ago
	markdown_file_path = Path(PLEX_GLOBALS['markdown_file'])
	if markdown_file_path.exists():
		file_mtime = datetime.datetime.fromtimestamp(markdown_file_path.stat().st_mtime)
		time_diff = datetime.datetime.now() - file_mtime
		if time_diff.total_seconds() < 86400:  # 86400 seconds = 1 day
			log_message(f"Skipping update: {markdown_file_path} was updated less than a day ago ({time_diff.total_seconds()/3600:.1f} hours ago)")
			return
	
	# Clear existing log file and markdown file
	clear_log()
	clear_markdown()
	
	# Log and write to markdown
	timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
	log_message(f"\n=== Plex Library Report ({timestamp}) ===")
	
	# Get movie statistics
	movie_stats = get_movie_stats(ssn)
	log_message("=== Movies ===")
	write_markdown("## Movies\n")
	
	log_message(f"Total Movies: {movie_stats['total']}")
	write_markdown(f"- **Total Movies:** {movie_stats['total']}")
	
	log_message(f"Watched: {movie_stats['watched']} ({movie_stats['watched']/movie_stats['total']*100:.1f}%)")
	write_markdown(f"- **Watched:** {movie_stats['watched']} ({movie_stats['watched']/movie_stats['total']*100:.1f}%)")
	
	log_message(f"Unwatched: {movie_stats['unwatched']} ({movie_stats['unwatched']/movie_stats['total']*100:.1f}%)\n")
	write_markdown(f"- **Unwatched:** {movie_stats['unwatched']} ({movie_stats['unwatched']/movie_stats['total']*100:.1f}%)\n")
	
	# Print detailed movie list
	log_message("=== Movie List ===")
	write_markdown("### Movie List\n")
	
	log_message("Title | Year | Watched | File Size | Genres")
	log_message("----------------------------------------")
	write_markdown("| Title | Year | Watched | File Size | Genres |")
	write_markdown("|-------|------|---------|-----------|--------|")
	
	movie_stats['movies_list'].sort(key=lambda x: re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of)\b', '', x['title'].lower()))
	
	for movie in movie_stats['movies_list']:
		watched_status = "Yes" if movie['watched'] else "No"
		genres_str = ", ".join(movie['genres']) if movie['genres'] else "None"
		log_message(f"{movie['title']} | {movie['year']} | {watched_status} | {movie['file_size']} | {genres_str}")
		write_markdown(f"| {movie['title']} | {movie['year']} | {watched_status} | {movie['file_size']} | {genres_str} |")
	
	# Get TV show statistics
	tv_stats = get_tv_stats(ssn)
	log_message("\n=== TV Shows ===")
	write_markdown("\n## TV Shows\n")
	
	log_message(f"Total Shows: {tv_stats['total_shows']}")
	write_markdown(f"- **Total Shows:** {tv_stats['total_shows']}")
	
	log_message(f"Total Episodes: {tv_stats['total_episodes']}")
	write_markdown(f"- **Total Episodes:** {tv_stats['total_episodes']}")
	
	log_message(f"Watched Episodes: {tv_stats['watched_episodes']} ({tv_stats['watched_episodes']/tv_stats['total_episodes']*100:.1f}%)")
	write_markdown(f"- **Watched Episodes:** {tv_stats['watched_episodes']} ({tv_stats['watched_episodes']/tv_stats['total_episodes']*100:.1f}%)")
	
	log_message(f"Unwatched Episodes: {tv_stats['unwatched_episodes']} ({tv_stats['unwatched_episodes']/tv_stats['total_episodes']*100:.1f}%)\n")
	write_markdown(f"- **Unwatched Episodes:** {tv_stats['unwatched_episodes']} ({tv_stats['unwatched_episodes']/tv_stats['total_episodes']*100:.1f}%)\n")
	
	# Print detailed TV show stats
	log_message("=== TV Show Details ===")
	write_markdown("### TV Show Details\n")
	
	log_message("Title | Episodes | Watched | % Watched | Total Size | Avg Episode Size | Genres")
	log_message("----------------------------------------")
	write_markdown("| Title | Episodes | Watched | % Watched | Total Size | Avg Episode Size | Genres |")
	write_markdown("|-------|----------|---------|-----------|------------|-----------------|--------|")
	
	tv_stats['shows_stats'].sort(key=lambda x: re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of)\b', '', x['title'].lower()))
	
	for show in sorted(tv_stats['shows_stats'], key=lambda x: x['title']):
		genres_str = ", ".join(show['genres']) if show['genres'] else "None"
		log_message(f"{show['title']} | {show['episodes']} | {show['watched']} | {show['percent_watched']:.1f}% | {show['file_size']} | {show['avg_episode_size']} | {genres_str}")
		write_markdown(f"| {show['title']} | {show['episodes']} | {show['watched']} | {show['percent_watched']:.1f}% | {show['file_size']} | {show['avg_episode_size']} | {genres_str} |")

	# Add storage statistics section
	log_message("\n=== Storage Statistics ===")
	write_markdown("\n## Storage Statistics\n")

	# Calculate total disk space used
	total_movie_size = sum(float(m['file_size'].split()[0]) * (1024 if m['file_size'].split()[1] == 'KB' else 1024**2 if m['file_size'].split()[1] == 'MB' else 1024**3 if m['file_size'].split()[1] == 'GB' else 1024**4) for m in movie_stats['movies_list'])
	total_tv_size = sum(float(s['file_size'].split()[0]) * (1024 if s['file_size'].split()[1] == 'KB' else 1024**2 if s['file_size'].split()[1] == 'MB' else 1024**3 if s['file_size'].split()[1] == 'GB' else 1024**4) for s in tv_stats['shows_stats'])
	total_size = total_movie_size + total_tv_size

	log_message(f"Total Disk Space Used: {format_size(total_size)}")
	write_markdown(f"- **Total Disk Space Used:** {format_size(total_size)}")

	# Top 10 largest movies
	log_message("\n=== Top 10 Largest Movies ===")
	write_markdown("\n### Top 10 Largest Movies\n")
	write_markdown("| Title | Year | File Size |")
	write_markdown("|-------|------|-----------|")

	# Sort movies by size (converting to bytes for comparison)
	largest_movies = sorted(movie_stats['movies_list'], 
		key=lambda x: float(x['file_size'].split()[0]) * (1024 if x['file_size'].split()[1] == 'KB' else 1024**2 if x['file_size'].split()[1] == 'MB' else 1024**3 if x['file_size'].split()[1] == 'GB' else 1024**4),
		reverse=True)[:10]

	for movie in largest_movies:
		log_message(f"{movie['title']} | {movie['year']} | {movie['file_size']}")
		write_markdown(f"| {movie['title']} | {movie['year']} | {movie['file_size']} |")

	# Top 10 TV shows by average episode size
	log_message("\n=== Top 10 TV Shows by Average Episode Size ===")
	write_markdown("\n### Top 10 TV Shows by Average Episode Size\n")
	write_markdown("| Title | Episodes | Average Episode Size |")
	write_markdown("|-------|----------|---------------------|")

	# Sort shows by average episode size (converting to bytes for comparison)
	largest_shows = sorted(tv_stats['shows_stats'],
		key=lambda x: float(x['avg_episode_size'].split()[0]) * (1024 if x['avg_episode_size'].split()[1] == 'KB' else 1024**2 if x['avg_episode_size'].split()[1] == 'MB' else 1024**3 if x['avg_episode_size'].split()[1] == 'GB' else 1024**4),
		reverse=True)[:10]

	for show in largest_shows:
		log_message(f"{show['title']} | {show['episodes']} | {show['avg_episode_size']}")
		write_markdown(f"| {show['title']} | {show['episodes']} | {show['avg_episode_size']} |")

	# Add combined genre statistics section
	log_message("\n=== Combined Genre Statistics ===")
	write_markdown("\n## Combined Genre Statistics\n")

	# Combine movie and TV show genres
	combined_genre_counts = {}
	for genre, count in movie_stats['genre_counts'].items():
		combined_genre_counts[genre] = combined_genre_counts.get(genre, 0) + count
	for genre, count in tv_stats['genre_counts'].items():
		combined_genre_counts[genre] = combined_genre_counts.get(genre, 0) + count

	# Sort genres by count
	sorted_genres = sorted(combined_genre_counts.items(), key=lambda x: x[1], reverse=True)

	# Write combined genre statistics
	write_markdown("| Genre | Count |")
	write_markdown("|-------|-------|")
	for genre, count in sorted_genres:
		log_message(f"{genre}: {count}")
		write_markdown(f"| {genre} | {count} |")

def run_plex_report(file_location):
	# Initialize PLEX_GLOBALS
	global PLEX_GLOBALS
	PLEX_GLOBALS = initialize_plex_globals(file_location)

	# Setup session
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': PLEX_GLOBALS['plex_api_token']})

	# Test connectivity with IP fallback
	test_plex_connectivity_with_fallback(ssn, PLEX_GLOBALS)

	# Generate the report
	generate_report(ssn) 