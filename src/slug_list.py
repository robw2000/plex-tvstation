#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
This script lists all TV shows and movies from a Plex server along with their slugs.
The slugs are used by tvstation.py for playlist management and filtering.

Requirements (python3 -m pip install [requirement]):
	requests
	python-dotenv

Setup:
	Fill the variables in the .env file or set them as environment variables:
		plex_ip: The ip address of your plex server.
		plex_port: The port of your plex server. Usually 32400.
		plex_api_token: The api token for your plex server. This can be found by opening the plex web interface, opening the browser dev tools,
						and finding the value of the X-Plex-Token query parameter on any plex request.
"""
from os import getenv
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

PLEX_GLOBALS = {
	'plex_ip': getenv('plex_ip', '192.168.1.196'),
	'plex_port': getenv('plex_port', '32400'),
	'plex_api_token': getenv('plex_api_token', ''),
	'base_url': None
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
	base_url = get_base_url()
	sections = ssn.get(f'{base_url}/library/sections/').json()['MediaContainer']['Directory']
	
	movie_section_key = None
	tv_section_key = None
	
	for section in sections:
		if section['title'] == 'Movies':
			movie_section_key = section['key']
		if section['title'] == 'TV Shows':
			tv_section_key = section['key']

	return movie_section_key, tv_section_key

def get_movies(ssn, movie_section_key):
	"""
	Retrieves all movies from the Plex server.
	"""
	base_url = get_base_url()
	results = ssn.get(f'{base_url}/library/sections/{movie_section_key}/all', params={})
	results.raise_for_status()
	results_json = results.json()
	return results_json['MediaContainer']['Metadata']

def get_tv_shows(ssn, tv_section_key):
	"""
	Retrieves all TV shows from the Plex server.
	"""
	base_url = get_base_url()
	results = ssn.get(f'{base_url}/library/sections/{tv_section_key}/all', params={})
	results.raise_for_status()
	results_json = results.json()
	return results_json['MediaContainer']['Metadata']

def run_slug_list(file_location):
	# Adjust paths to use file_location
	logs_dir = file_location / 'logs'
	logs_dir.mkdir(exist_ok=True)

	"""
	Main function to print the list of all items and their slugs.
	"""
	# Setup session
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': PLEX_GLOBALS['plex_api_token']})

	# Get section keys
	movie_section_key, tv_section_key = get_section_keys(ssn)

	# Get all movies and TV shows
	movies = get_movies(ssn, movie_section_key)
	tv_shows = get_tv_shows(ssn, tv_section_key)

	# Print header
	print("\nMovies:")
	print("-" * 80)
	print(f"{'Title':<50} {'Slug':<30}")
	print("-" * 80)

	# Print movies
	for movie in movies:
		title = movie['title']
		slug = movie.get('slug', 'MISSING SLUG')
		print(f"{title:<50} {slug:<30}")

	# Print TV shows
	print("\nTV Shows:")
	print("-" * 80)
	print(f"{'Title':<50} {'Slug':<30}")
	print("-" * 80)

	for show in tv_shows:
		title = show['title']
		slug = show.get('slug', 'MISSING SLUG')
		print(f"{title:<50} {slug:<30}")

	# Print summary
	print("\nSummary:")
	print(f"Total Movies: {len(movies)}")
	print(f"Total TV Shows: {len(tv_shows)}")
