#!/usr/bin/python3
#-*- coding: utf-8 -*-

"""
The use case of this script is the following:
	Make a playlist that includes all unwatched movies and tv shows, starting with the next unwatched episode of each series or movie (first unwatched in shuffled list).
	Every time the script is run, it will rebuild the playlist based on the current state of the library.
	The shows will be sorted by their internal ratingKey which gives a random but consistent order.
	Movies are added to the list of shows as if all movies were part of a single series. Below, movies will be spoken of as a series.
	The series that was most recently watched is marked and the next series is selected as the first series in the playlist.
	From there, the next unwatched episode of each series are played, one per series, alternating between series.
	When all episodes of a series are watched, the series is then excluded from the playlist until the most recent viewedAt time is more than the configured rewatch delay period.
	Only unwatched movies and episodes are included in the playlist.
	Movies are grouped by series (e.g., Star Wars, John Wick) to maintain chronological order within the playlist.
	If the number of unwatched movies falls below 33% of the total (meaning at least two-thirds are watched), the script will automatically mark watched movies as unwatched based on the rewatch delay configuration.
	Movies with slugs that match entries in restricted_play_months will only be included if the current month matches.
	For example, movies with "christmas" in the slug will only be played in December if "christmas" is in the December entry in restricted_play_months.
	The script sends logs messages to both the console and a log file.

Requirements (python3 -m pip install [requirement]):
	requests
	python-dotenv

Setup:
	Fill the variables in the .env file or set them as environment variables:
		playlist_name: The name of the playlist that will be created/searched for. Choose a name for your playlist and use that name here.
		plex_ip: The ip address of your plex server.
		plex_port: The port of your plex server. Usually 32400.
		plex_api_token: The api token for your plex server. This can be found by opening the plex web interface, opening the browser dev tools,
						and finding the value of the X-Plex-Token query parameter on any plex request.
		user_id: The user id of the user that will be used to access the plex server. If you only have one user, it's probably 1.
		max_episodes: The maximum number of episodes that will be included in the playlist.
		omdb_api_key: (Optional) Your OMDB API key for fetching movie years.
		omdb_api_url: (Optional) The OMDB API URL. Defaults to http://www.omdbapi.com/.

	Create a local_config.json file to customize rewatch delays and metadata. You can use the provided local_config-example.json as a starting point:
	{
		"defaultRewatchDelayDays": {
			"movies": 180,
			"tv": 90
		},
		"excluded_slugs": ["example-series-1", "example-series-2"],
		"metadata": [
			{
				"slug": "movie-title",
				"title": "Movie Title",  # Optional: Alternative title to use for IMDB lookup
				"year": 1980,
				"rewatchDelayDays": 365
			}
		],
		"movie_series_slugs": ["star-wars", "john-wick", "indiana-jones"],
		"restricted_play_months": {
			"december": ["christmas", "santa", "elf"],
			"october": ["halloween", "ghost", "vampire"]
		}
	}

	Run the script at an interval to regularly update the playlist.
"""
from os import getenv, path, makedirs
import os
import time
import hashlib
import json
import glob
from dotenv import load_dotenv
import requests

# Ensure logs directory exists
logs_dir = path.join(path.dirname(path.abspath(__file__)), 'logs')
if not path.exists(logs_dir):
	makedirs(logs_dir)

def clean_old_logs():
	"""
	Deletes log files that are older than 3 days.
	"""
	current_time = time.time()
	three_days_ago = current_time - (3 * 24 * 60 * 60)  # 3 days in seconds
	
	# Get all log files in the logs directory
	log_files = glob.glob(path.join(logs_dir, '*.log'))
	
	for log_file in log_files:
		# Get the file's modification time
		file_time = os.path.getmtime(log_file)
		
		# If the file is older than 3 days, delete it
		if file_time < three_days_ago:
			try:
				os.remove(log_file)
				print(f"Deleted old log file: {log_file}")
			except Exception as e:
				print(f"Error deleting log file {log_file}: {e}")

# Clean up old log files
clean_old_logs()

# Create log file with date prefix
current_date = time.strftime('%Y-%m-%d')
log_file = path.join(logs_dir, f'{current_date}-tvstation.log')
if path.exists(log_file):
	os.remove(log_file)

# Clear the log file
with open(log_file, 'w') as f:
	f.write(f"Log file created at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def log_message(*args, **kwargs):
	"""
	Log a message to both the log file and stdout.
	This function takes the same arguments as the print function.
	"""
	# Get the current timestamp
	timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
	
	# Format the message
	message = ' '.join(str(arg) for arg in args)
	
	# Print to stdout only if not in log-only mode
	if not PLEX_GLOBALS.get('log_only', False):
		print(*args, **kwargs)
	
	# Write to log file
	with open(log_file, 'a') as f:
		f.write(f"[{timestamp}] {message}\n")

# Load environment variables from .env file
load_dotenv()

# Load missing metadata from JSON file
try:
	with open('local_config.json', 'r') as f:
		LOCAL_CONFIG = json.load(f)
except FileNotFoundError:
	LOCAL_CONFIG = {
		"defaultRewatchDelayDays": {
			"movies": 180,
			"tv": 90
		},
		"excluded_slugs": [],
		"metadata": [],
		"movie_series_slugs": [],
		"restricted_play_months": {}
	}

PLEX_GLOBALS = {
	'playlist_name': getenv('playlist_name', 'My Favs TV'),
	'plex_ip': getenv('plex_ip', '192.168.1.196'),
	'plex_port': getenv('plex_port', '32400'),
	'plex_api_token': getenv('plex_api_token', ''),
	'user_id': getenv('user_id', '1'),
	'max_episodes': int(getenv('max_episodes', 50)),
	'excluded_slugs': LOCAL_CONFIG.get('excluded_slugs', []),
	'omdb_api_key': getenv('omdb_api_key', ''),
	'omdb_api_url': getenv('omdb_api_url', 'http://www.omdbapi.com/'),
	'defaultRewatchDelayDays': LOCAL_CONFIG.get('defaultRewatchDelayDays', {'movies': 180, 'tv': 90}),
	'metadata': LOCAL_CONFIG.get('metadata', []),
	'movie_series_slugs': LOCAL_CONFIG.get('movie_series_slugs', []),
	'restricted_play_months': LOCAL_CONFIG.get('restricted_play_months', {}),

	'base_url': None,
	'machine_id': None,
	'playlist_key': None,
	'movies_section_key': None,
	'tv_section_key': None,

	'series_keys': [],  # List of objects with {key, last_viewed_at} properties
	'series_seasons': {},
	'series_episodes': {},

	'playlist_episode_keys': []
}

def load_globals(ssn):
	"""
	Initializes global variables by fetching the base URL, section keys for Movies and TV Shows,
	and the playlist key from the Plex server. This should be called once at startup to populate
	the PLEX_GLOBALS dictionary with required values.
	"""
	get_base_url()
	clean_restricted_play_months()
	get_section_keys(ssn)
	get_playlist_key(ssn)

def get_base_url():
	"""
	Retrieves the base URL for the Plex server.
	"""
	if PLEX_GLOBALS['base_url'] is not None:
		return PLEX_GLOBALS['base_url']

	PLEX_GLOBALS['base_url'] = f"http://{PLEX_GLOBALS['plex_ip']}:{PLEX_GLOBALS['plex_port']}"
	return PLEX_GLOBALS['base_url']

def get_machine_id(ssn):
	"""
	Retrieves the machine identifier for the Plex server.
	"""
	if PLEX_GLOBALS['machine_id'] is not None:
		return PLEX_GLOBALS['machine_id']

	base_url = get_base_url()
	PLEX_GLOBALS['machine_id'] = ssn.get(f'{base_url}/').json()['MediaContainer']['machineIdentifier']
	return PLEX_GLOBALS['machine_id']

def get_playlist_key(ssn):
	"""
	Retrieves the playlist key for the Plex server.
	"""
	base_url = get_base_url()
	playlist_name, playlist_key, _, _ = get_playlist_globals()

	if playlist_key is not None:
		return playlist_key

	params = {'playlistType': 'video', 'includeCollections': '1'}
	if playlist_key is not None:
		playlists = ssn.get(f'{base_url}/playlists/{playlist_key}', params=params).json()['MediaContainer']['Metadata']
	else:
		playlists = ssn.get(f'{base_url}/playlists', params={'playlistType': 'video', 'includeCollections': '1'}).json()['MediaContainer']['Metadata']

	for pl in playlists:
		if pl['title'] == playlist_name:
			playlist_key = pl['ratingKey']
			break

	PLEX_GLOBALS['playlist_key'] = playlist_key
	return playlist_key

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

def get_series_globals():
	"""
	Retrieves the series keys, seasons, and episodes from the Plex server.
	"""
	return PLEX_GLOBALS['series_keys'], PLEX_GLOBALS['series_seasons'], PLEX_GLOBALS['series_episodes']

def get_playlist_globals():
	"""
	Retrieves the playlist name, key, episode keys, and maximum episodes from the PLEX_GLOBALS dictionary.
	"""
	return PLEX_GLOBALS['playlist_name'], PLEX_GLOBALS['playlist_key'], PLEX_GLOBALS['playlist_episode_keys'], PLEX_GLOBALS['max_episodes']

def refresh_movies(ssn):
	"""
	Refreshes the movie library on the Plex server.
	"""
	base_url = get_base_url()
	movie_section_key, _ = get_section_keys(ssn)

	refresh_result = ssn.get(f'{base_url}/library/sections/{movie_section_key}/refresh?force=1')
	if refresh_result.status_code != 200:
		log_message(f"Error refreshing movie shows: {refresh_result.status_code}")
	else:
		log_message("Movie shows refreshed")

def refresh_tv_shows(ssn):
	"""
	Refreshes the TV show library on the Plex server.
	"""
	base_url = get_base_url()
	_, tv_section_key = get_section_keys(ssn)

	refresh_result = ssn.get(f'{base_url}/library/sections/{tv_section_key}/refresh?force=1')
	if refresh_result.status_code != 200:
		log_message(f"Error refreshing tv shows: {refresh_result.status_code}")
	else:
		log_message("Tv shows refreshed")

def mark_as_unwatched(ssn, media_key):
	"""
	Unscrobbles a media item from the Plex server.
	Scrobbling is the process of marking a media item as watched. This function marks a media item as unwatched.
	"""
	base_url = get_base_url()
	ssn.get(f'{base_url}/:/unscrobble?identifier=com.plexapp.plugins.library&key={media_key}')

def create_slug(title):
	"""
	Creates a slug from a title by converting to lowercase, replacing spaces with dashes,
	and removing any characters that are not letters or dashes.
	"""
	slug = ''.join(c.lower() if c.isalpha() or c == ' ' else '' for c in title)
	return '-'.join(slug.split())

def get_movie_year_from_imdb(movie_title):
	"""
	Attempts to get the release year of a movie from the IMDB API using the movie title.
	Returns the year if found, otherwise returns 0.
	"""
	
	try:
		# Use the OMDB API which is free and doesn't require authentication
		api_key = PLEX_GLOBALS['omdb_api_key']
		api_url = PLEX_GLOBALS['omdb_api_url']
		if not api_key:
			log_message(f"Warning: OMDB API key not found. Cannot fetch year for movie: {movie_title}")
			return 0
		
		# Keep cutting off the last word until we get a response
		adjusted_movie_title = movie_title
		while adjusted_movie_title != '':
			response = requests.get(f"{api_url}?s={adjusted_movie_title}&apikey={api_key}")
			data = response.json() if response.status_code == 200 and response.json().get('Response') == 'True' else None
			if data and len(data.get('Search', [])) > 0:
				return int(data.get('Search')[0].get('Year'), 0)
			adjusted_movie_title = adjusted_movie_title.rsplit(' ', 1)[0] if len(adjusted_movie_title.split(' ')) > 1 else ''
	except Exception as e:
		log_message(f"Error fetching movie year from IMDB: {e}")
	
	return 0

def build_series_episodes(ssn):
	"""
	Builds the series episodes for the Plex server.
	Retrieves all series and their seasons from the Plex server and builds a list of episodes for each series.
	Each series is then sorted by the date of the most recently watched episode, starting with the episode after the most recently watched episode.
	"""
	base_url = get_base_url()
	_, tv_section_key = get_section_keys(ssn)
	series_keys, series_seasons, series_episodes = get_series_globals()

	series_list = ssn.get(f'{base_url}/library/sections/{tv_section_key}/all', params={}).json()['MediaContainer']['Metadata']

	# Get all series and their seasons
	for s in series_list:
		series_slug = s.get('slug', create_slug(s['title']))
		if series_slug in PLEX_GLOBALS['excluded_slugs']:
			continue

		series_key = s['ratingKey']
		series_seasons[series_key] = ssn.get(f'{base_url}/library/metadata/{series_key}/children', params={}).json()['MediaContainer']['Metadata']
		series_episodes[series_key] = []

		# Get all episodes and their watched status
		# Track episode keys and whether they are watched or not
		first_unwatched_episode = None
		start_index = 0
		overall_index = 0  # Changed from -1 to 0 to make it 1-indexed
		most_recent_viewed_at = 0

		for season in series_seasons[series_key]:
			season_key = season["ratingKey"]

			episodes = ssn.get(f'{base_url}/library/metadata/{season_key}/children', params={}).json()['MediaContainer']['Metadata']
			for episode in episodes:
				overall_index += 1  # Increment first to make it 1-indexed
				episode_key = episode['ratingKey']
				last_viewed_at = episode.get('lastViewedAt', 0)
				view_count = episode.get('viewCount', 0)
				episode['index'] = overall_index
				
				series_episodes[series_key].append({
					'ratingKey': episode_key,
					'index': overall_index,
					'type': 'tv',
					'lastViewedAt': last_viewed_at,
					'isWatched': view_count > 0,
					'title': f'{episode["parentTitle"]} Episode {str(episode["index"])} - {episode["title"]}',
					'series_title': episode['grandparentTitle']
				})
				if first_unwatched_episode is None and view_count == 0:
					first_unwatched_episode = episode
					start_index = overall_index
				else:
					# Save the viewed time of the last watched episode before the first unwatched episode was found
					if last_viewed_at > most_recent_viewed_at:
						most_recent_viewed_at = last_viewed_at

		# Add the series keys with the most recent viewed at time
		series_keys.append({'key': series_key, 'last_viewed_at': most_recent_viewed_at})

		# If all episodes are watched, mark them as unwatched
		all_watched = first_unwatched_episode is None
		if all_watched:
			# Get the rewatch delay days from LOCAL_CONFIG
			series_config = next((item for item in PLEX_GLOBALS['metadata'] if item.get('slug') == series_slug), {})
			rewatch_delay_days = series_config.get('rewatchDelayDays', PLEX_GLOBALS['defaultRewatchDelayDays']['tv'])
			
			if (time.time() - most_recent_viewed_at) >= (rewatch_delay_days * 24 * 60 * 60):  # Convert days to seconds
				mark_as_unwatched(ssn, series_key)
			else:
				# If all episodes are watched but the rewatch delay has not passed, remove the series from the playlist
				PLEX_GLOBALS['series_keys'] = [obj for obj in PLEX_GLOBALS['series_keys'] if obj['key'] != series_key]
				del series_episodes[series_key]

		if start_index > 0 and series_episodes.get(series_key) is not None:
			series_episodes[series_key] = series_episodes[series_key][start_index:]

def build_movie_list(ssn):
	"""
	Builds the movie list for the Plex server.
	Retrieves all movies from the Plex server and sorts them by year.
	The movies are then added to the series_episodes list as if they were a TV show.
	The movies are then sorted by the date of the most recently watched movie, starting with the movie after the most recently watched movie.
	Movies with slugs that match entries in restricted_play_months will only be included if the current month matches.
	For example, movies with "christmas" in the slug will only be played in December if "christmas" is in the December entry in restricted_play_months.
	Movies are grouped by series (e.g., Star Wars, John Wick) to maintain chronological order within the playlist.
	If the number of unwatched movies falls below 33% of the total, the script will automatically mark watched movies as unwatched based on the rewatch delay configuration.
	"""
	base_url = get_base_url()
	movie_section_key, _ = get_section_keys(ssn)
	_, _, series_episodes = get_series_globals()

	# Get current month for restricted play check
	current_month = time.strftime("%B").lower()

	results = ssn.get(f'{base_url}/library/sections/{movie_section_key}/all', params={})
	results.raise_for_status()
	results_json = results.json()
	movie_list = results_json['MediaContainer']['Metadata']

	movie_list = sorted(movie_list, key=lambda x: hashlib.md5(x['title'].encode()).hexdigest())
	for movie in movie_list:
		movie['index'] = movie_list.index(movie)
	
	# Track total movies for the unwatched threshold
	total_movies = len(movie_list)
	
	# Filter out movies whose slugs are in the excluded_slugs list or restricted by month
	filtered_movie_list = []
	for movie in movie_list:
		movie_slug = movie.get('slug', create_slug(movie['title']))
		if movie_slug in PLEX_GLOBALS['excluded_slugs']:
			continue
			
		# Check if movie is restricted by month
		is_restricted = False
		for month, slugs in PLEX_GLOBALS['restricted_play_months'].items():
			# Ensure slugs is a list, defaulting to empty if not present
			slugs_list = slugs if isinstance(slugs, list) else []
			if month.lower() != current_month.lower():
				# Check if any of the partial slugs are contained within the movie's slug
				for partial_slug in slugs_list:
					if partial_slug.lower() in movie_slug:
						is_restricted = True
						break
				if is_restricted:
					break
				
		if is_restricted:
			continue
			
		filtered_movie_list.append(movie)
	
	movie_list = filtered_movie_list
	total_movies = len(movie_list)
	most_recent_viewed_at = 0

	for movie in movie_list:
		# Track the most recent viewed movie
		last_viewed_at = movie.get('lastViewedAt', 0)
		if last_viewed_at > most_recent_viewed_at:
			most_recent_viewed_at = last_viewed_at

		if movie.get('year', 0) == 0:
			# Use existing slug or create new one
			movie_slug = movie.get('slug', create_slug(movie['title']))
			movie_config = next((item for item in PLEX_GLOBALS['metadata'] if item.get('slug') == movie_slug), {})
			if movie_config and movie_config.get('year', 0) > 0:
				movie['year'] = movie_config.get('year', 0)
				movie['slug'] = movie_config.get('slug', movie_slug)
			else:
				# Try to get the year from IMDB API
				# Use title from local config if available, otherwise use movie title
				imdb_title = movie_config.get('title', movie['title'])
				movie['year'] = get_movie_year_from_imdb(imdb_title)
				if movie['year'] == 0:
					log_message(f"Warning: Could not determine year for movie: {movie['title']}")

	# Check if we've reached the threshold (33% or less unwatched)
	unwatched_count = len([m for m in movie_list if m.get('viewCount', 0) == 0])
	if unwatched_count / total_movies <= 0.33:
		log_message(f"\nOnly {unwatched_count} of {total_movies} movies are unwatched ({(unwatched_count / total_movies) * 100:.1f}%)")
		log_message("Checking for movies to mark as unwatched...")
		
		# Go through all movies and check rewatch delays for watched ones
		for movie in movie_list:
			if movie.get('viewCount', 0) > 0:  # If movie is watched
				movie_slug = movie.get('slug', create_slug(movie['title']))
				movie_config = next((item for item in PLEX_GLOBALS['metadata'] if item.get('slug') == movie_slug), {})
				rewatch_delay_days = movie_config.get('rewatchDelayDays', PLEX_GLOBALS['defaultRewatchDelayDays']['movies'])
				
				last_viewed_at = movie.get('lastViewedAt', 0)
				if last_viewed_at > 0 and (time.time() - last_viewed_at) >= (rewatch_delay_days * 24 * 60 * 60):
					log_message(f"Marking as unwatched: {movie['title']} (last watched {time.strftime('%Y-%m-%d', time.localtime(last_viewed_at))})")
					mark_as_unwatched(ssn, movie['ratingKey'])

	for movie in movie_list:
		movie['isWatched'] = movie.get('viewCount', 0) > 0
		movie['lastViewedAt'] = movie.get('lastViewedAt', 0)
		if str(movie["year"]) in movie['title']:
			movie['title'] = movie['title'].rsplit(' ', 1)[0]
		movie['title'] = f'{movie["title"]} ({str(movie["year"])})'
		movie['series_title'] = 'Movies'
		movie_slug = movie.get('slug', create_slug(movie['title']))
		key_word_parts = filter_common_words(movie_slug)
		
		# Check if the movie slug starts with any of the movie series slugs from PLEX_GLOBALS
		movie['key_word'] = key_word_parts[0]  # Default to first word
		
		for series_slug in PLEX_GLOBALS['movie_series_slugs']:
			series_slug_parts = filter_common_words(series_slug)
			trimmed_series_slug = '-'.join(series_slug_parts)
			if trimmed_series_slug in movie_slug:
				movie['key_word'] = series_slug
				break

	# Sort the movies by a hash of the title which will randomize the sort but also ensure the sort is the same each time
	unwatched_movies = list(filter(lambda x: not x['isWatched'], movie_list))

	# Group the movies by key word
	key_word_map = {}
	for i in range(len(unwatched_movies)):
		key_word = unwatched_movies[i]['key_word']
		if key_word not in key_word_map:
			key_word_map[key_word] = []
		key_word_map[key_word].append({'index': i, 'movie': unwatched_movies[i]})

	# ensure that movies in the same series (star wars, john wick, etc.) appear in order by year through the otherwise shuffled list
	for key_word in key_word_map:
		movies = key_word_map[key_word]
		if len(movies) < 2:
			continue

		movies.sort(key=lambda x: x['movie']['year'])
		indexes = [movie['index'] for movie in movies]
		indexes.sort()
		for i in range(len(indexes)):
			unwatched_movies[indexes[i]] = movies[i]['movie']

	# Add movies to series_keys with last_viewed_at of 0
	PLEX_GLOBALS['series_keys'].append({'key': 'movies', 'last_viewed_at': most_recent_viewed_at})
	series_episodes['movies'] = unwatched_movies

def build_playlist_episode_keys():
	"""
	Builds the playlist episode keys for the Plex server.
	Retrieves all series and their episodes from the Plex server and builds a list of episode keys for the playlist.
	An episode is selected from each series and added to the playlist, alternating between series.
	This results in a playlist that rotates between all series, with each series being watched in order, starting with the most recently watched episode.
	"""
	series_keys, _, series_episodes = get_series_globals()
	_, _, playlist_episode_keys, max_episodes = get_playlist_globals()

	# Sort the series keys by last_viewed_at (most recent viewed last)
	series_keys = sorted(series_keys, key=lambda x: x['last_viewed_at'], reverse=False)

	# Build the playlist episode keys
	log_message('')
	log_message('Playlist episodes')
	log_message('--------------------------')

	episode_indexes = {}
	while len(playlist_episode_keys) < max_episodes:
		for series_obj in series_keys:
			series_key = series_obj['key']
			next_index = episode_indexes.get(series_key, episode_indexes.get(series_key, 0))
			if next_index >= len(series_episodes[series_key]):
				continue

			ekey = series_episodes[series_key][next_index]['ratingKey']
			playlist_episode_keys.append(ekey)
			episode_indexes[series_key] = (next_index + 1) % len(series_episodes[series_key])

			episode = series_episodes[series_key][next_index]
			log_message(f'{episode["series_title"]}: {episode["title"]}')


def get_playlist_episode(ssn):
	"""
	Retrieves the list of episode keys in the current version of the playlist from the Plex server.
	"""
	base_url = get_base_url()
	playlist_name, playlist_key, _, _ = get_playlist_globals()

	params = {'playlistType': 'video', 'includeCollections': '1'}
	if playlist_key is not None:
		playlists = ssn.get(f'{base_url}/playlists/{playlist_key}', params=params).json()['MediaContainer']['Metadata']
	else:
		playlists = ssn.get(f'{base_url}/playlists', params={'playlistType': 'video', 'includeCollections': '1'}).json()['MediaContainer']['Metadata']

	for pl in playlists:
		if pl['title'] == playlist_name:
			playlist_key = pl['ratingKey']
			break

	if playlist_key is None:
		return []

	# Get all items in the playlist
	items = ssn.get(f'{base_url}/playlists/{playlist_key}/items', params=params).json()['MediaContainer']['Metadata']

	return items

def replace_playlist_items(ssn):
	"""
	Creates the playlist if it doesn't exist, or updates it if it does.
	"""
	base_url = get_base_url()
	machine_id = get_machine_id(ssn)
	playlist_name, playlist_key, playlist_episode_keys, _ = get_playlist_globals()

	params = {'type': 'video', 'title': playlist_name, 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(playlist_episode_keys)}'}

	if playlist_key is not None:
		# Delete existing playlist
		response = ssn.delete(f'{base_url}/playlists/{playlist_key}')

	# Create new playlist
	response = ssn.post(f'{base_url}/playlists', params=params)

	return response

def rob_tv(ssn):
	"""
	Main function to orchestrate the playlist creation and update process.
	"""
	# Load global variables
	load_globals(ssn)

	# Refresh the library to ensure any new content is included
	refresh_tv_shows(ssn)
	build_series_episodes(ssn)

	# Build the list of movies and TV show episodes
	refresh_movies(ssn)
	build_movie_list(ssn)

	# Build the list of playlist episodes/movies
	build_playlist_episode_keys()

	# Replace the playlist items with the new list
	response = replace_playlist_items(ssn)

	return response

def find_index(lst, predicate):
	"""
	Finds the index of the first element in the list that satisfies the predicate.
	"""
	return next((i for i, x in enumerate(lst) if predicate(x)), -1)

def clean_restricted_play_months():
	"""
	Cleans the restricted_play_months dictionary to ensure all keys are valid month names in lowercase.
	This function validates the month names in the restricted_play_months configuration and ensures they are in lowercase.
	It also ensures that the values are lists, defaulting to empty lists if not.
	This is used to restrict certain movies to only play during specific months of the year.
	"""
	valid_months = [
		"january", "february", "march", "april", "may", "june",
		"july", "august", "september", "october", "november", "december"
	]
	
	validated_months = {}
	
	# Process each month in the input dictionary
	for month, slugs in PLEX_GLOBALS['restricted_play_months'].items():
		# Convert month to lowercase
		month_lower = month.lower()
		
		# Check if it's a valid month
		if month_lower in valid_months:
			# Ensure slugs is a list
			slugs_list = slugs if isinstance(slugs, list) else []
			validated_months[month_lower] = slugs_list
		else:
			log_message(f"Warning: Invalid month '{month}' in restricted_play_months. Skipping...")
	
	# Add any missing months with empty lists
	for month in valid_months:
		if month not in validated_months:
			validated_months[month] = []
	
	return validated_months

def filter_common_words(slug):
	"""
	Filters out common words from a slug.
	Returns a list of words with common words like 'the', 'a', 'an' removed.
	"""
	return list(filter(lambda x: x != 'the' and x != 'a' and x != 'an', slug.split('-')))

# ------------------------------------------
# Main
# ------------------------------------------
if __name__ == '__main__':
	import requests, argparse

	#setup vars
	ssn = requests.Session()
	ssn.headers.update({'Accept': 'application/json'})
	ssn.params.update({'X-Plex-Token': PLEX_GLOBALS['plex_api_token']})

	#setup arg parsing
	parser = argparse.ArgumentParser(description='Make a playlist out of all tv shows and movies, starting with the next unwatched episode of each series or movie by year')
	parser.add_argument('-p','--PlaylistName', type=str, help='Name of target playlist', default=PLEX_GLOBALS['playlist_name'])
	parser.add_argument('-l', '--log-only', action='store_true', help='Only write to log files, do not print to stdout')

	args = parser.parse_args()

	# Set log-only mode if specified
	PLEX_GLOBALS['log_only'] = args.log_only
	
	# If log-only mode is enabled, print a log entry to stdout
	if args.log_only:
		timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
		script_name = os.path.basename(__file__)
		args_str = ' '.join([f"{k}={v}" for k, v in vars(args).items() if v is not None])
		print(f"[{timestamp}] Running {script_name} with args: {args_str}")

	#call function and process result
	response = rob_tv(ssn=ssn)
	if response.status_code != 200:
		log_message("ERROR: Playlist could not be updated!")
		parser.error(response)

	log_message("Playlist updated successfully!")
