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

from os import getenv, path, makedirs
import re
import time
from dotenv import load_dotenv
import requests

# Ensure logs directory exists
logs_dir = path.join(path.dirname(path.abspath(__file__)), '../logs')
if not path.exists(logs_dir):
	makedirs(logs_dir)

# Create log file with date prefix
current_date = time.strftime('%Y-%m-%d')
log_file = path.join(logs_dir, f'{current_date}-plex_library_report.log')
markdown_file = path.join(logs_dir, 'library-media.md')

def log_message(*args, **kwargs):
	"""
	Log a message to both the log file and stdout.
	This function takes the same arguments as the print function.
	"""
	# Get the current timestamp
	timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
	
	# Format the message
	message = ' '.join(str(arg) for arg in args)
	
	# Print to stdout
	print(*args, **kwargs)
	
	# Write to dated log file
	with open(log_file, 'a') as f:
		f.write(f"[{timestamp}] {message}\n")

def write_markdown(*args, **kwargs):
	"""
	Write a message to the markdown file.
	This function takes the same arguments as the print function.
	"""
	# Format the message
	message = ' '.join(str(arg) for arg in args)
	
	# Write to markdown file
	with open(markdown_file, 'a') as f:
		f.write(f"{message}\n")

def clear_markdown():
	"""
	Clear the markdown file and add the header.
	"""
	with open(markdown_file, 'w') as f:
		f.write("# Plex Library Report\n\n")
		f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

# Load environment variables from .env file
load_dotenv()

PLEX_GLOBALS = {
	'plex_ip': getenv('plex_ip', '192.168.1.196'),
	'plex_port': getenv('plex_port', '32400'),
	'plex_api_token': getenv('plex_api_token', ''),
	'user_id': getenv('user_id', '1'),
	'base_url': None,
	'movies_section_key': None,
	'tv_section_key': None
}

def get_base_url():
	"""
	Retrieves the base URL for the Plex server.
	"""
	if PLEX_GLOBALS['base_url'] is not None:
		return PLEX_GLOBALS['base_url']

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

def get_movie_stats(ssn):
	"""
	Retrieves statistics about movies in the library.
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
	for movie in movie_list:
		movies_list.append({
			'title': movie['title'],
			'year': movie.get('year', 'Unknown'),
			'watched': movie.get('viewCount', 0) > 0
		})
	
	return {
		'total': total_movies,
		'watched': watched_movies,
		'unwatched': unwatched_movies,
		'movies_list': sorted(movies_list, key=lambda x: (x['year'], x['title']))
	}

def get_tv_stats(ssn):
	"""
	Retrieves statistics about TV shows in the library.
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
	for series in series_list:
		series_key = series['ratingKey']
		seasons = ssn.get(f'{base_url}/library/metadata/{series_key}/children', params={}).json()['MediaContainer']['Metadata']
		
		show_episodes = 0
		show_watched = 0
		
		for season in seasons:
			season_key = season['ratingKey']
			episodes = ssn.get(f'{base_url}/library/metadata/{season_key}/children', params={}).json()['MediaContainer']['Metadata']
			
			show_episodes += len(episodes)
			show_watched += len([e for e in episodes if e.get('viewCount', 0) > 0])
		
		total_episodes += show_episodes
		watched_episodes += show_watched
		
		shows_stats.append({
			'title': series['title'],
			'episodes': show_episodes,
			'watched': show_watched,
			'percent_watched': (show_watched / show_episodes * 100) if show_episodes > 0 else 0
		})
	
	return {
		'total_shows': total_shows,
		'total_episodes': total_episodes,
		'watched_episodes': watched_episodes,
		'unwatched_episodes': total_episodes - watched_episodes,
		'shows_stats': shows_stats
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
	Generates a comprehensive report of the Plex library.
	"""
	# Clear and initialize markdown file
	clear_markdown()
	
	# Log and write to markdown
	log_message("\n=== Plex Library Report ===")
	
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
	
	log_message("Title | Year | Watched")
	log_message("----------------------------------------")
	write_markdown("| Title | Year | Watched |")
	write_markdown("|-------|------|---------|")
	
	movie_stats['movies_list'].sort(key=lambda x: re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of)\b', '', x['title'].lower()))
	
	for movie in movie_stats['movies_list']:
		watched_status = "Yes" if movie['watched'] else "No"
		log_message(f"{movie['title']} | {movie['year']} | {watched_status}")
		write_markdown(f"| {movie['title']} | {movie['year']} | {watched_status} |")
	
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
	
	log_message("Title | Episodes | Watched | % Watched")
	log_message("----------------------------------------")
	write_markdown("| Title | Episodes | Watched | % Watched |")
	write_markdown("|-------|----------|---------|-----------|")
	
	tv_stats['shows_stats'].sort(key=lambda x: re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of)\b', '', x['title'].lower()))
	
	for show in sorted(tv_stats['shows_stats'], key=lambda x: x['title']):
		log_message(f"{show['title']} | {show['episodes']} | {show['watched']} | {show['percent_watched']:.1f}%")
		write_markdown(f"| {show['title']} | {show['episodes']} | {show['watched']} | {show['percent_watched']:.1f}% |")

def run_plex_report(file_location):
	# Adjust paths to use file_location
	logs_dir = file_location / 'logs'
	logs_dir.mkdir(exist_ok=True)

	# Setup session
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': PLEX_GLOBALS['plex_api_token']})

	# Generate the report
	generate_report(ssn) 