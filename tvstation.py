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
		]
	}

	Run the script at an interval to regularly update the playlist.
"""
from os import getenv
import time
import hashlib
import json
from dotenv import load_dotenv
import requests

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
		"movie_series_slugs": []
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

	'base_url': None,
	'machine_id': None,
	'playlist_key': None,
	'movies_section_key': None,
	'tv_section_key': None,

	'series_keys': [],
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
		print(f"Error refreshing movie shows: {refresh_result.status_code}")
	else:
		print("Movie shows refreshed")

def refresh_tv_shows(ssn):
	"""
	Refreshes the TV show library on the Plex server.
	"""
	base_url = get_base_url()
	_, tv_section_key = get_section_keys(ssn)

	refresh_result = ssn.get(f'{base_url}/library/sections/{tv_section_key}/refresh?force=1')
	if refresh_result.status_code != 200:
		print(f"Error refreshing tv shows: {refresh_result.status_code}")
	else:
		print("Tv shows refreshed")

def mark_as_unwatched(ssn, media_key):
	"""
	Unscrobbles a media item from the Plex server.
	Scrobbling is the process of marking a media item as watched. This function marks a media item as unwatched.
	"""
	base_url = get_base_url()
	ssn.get(f'{base_url}/:/unscrobble?key={media_key}')

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
			print(f"Warning: OMDB API key not found. Cannot fetch year for movie: {movie_title}")
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
		print(f"Error fetching movie year from IMDB: {e}")
	
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
		series_keys.append(series_key)
		series_seasons[series_key] = ssn.get(f'{base_url}/library/metadata/{series_key}/children', params={}).json()['MediaContainer']['Metadata']
		series_episodes[series_key] = []

		# Get all episodes and their watched status
		# Track episode keys and whether they are watched or not
		first_unwatched_episode = None
		start_index = 0
		most_recent_viewed_at = 0
		for season in series_seasons[series_key]:
			overall_index = -1
			season_key = season["ratingKey"]

			unwatched_response = ssn.get(f'{base_url}/library/metadata/{season_key}/children?unwatched=1')
			unwatched = unwatched_response.json().get('MediaContainer', {}).get('Metadata', [])
			unwatched_key_set = set([x['ratingKey'] for x in unwatched])

			episodes = ssn.get(f'{base_url}/library/metadata/{season_key}/children', params={}).json()['MediaContainer']['Metadata']
			# last_watched_episode = None
			for i, episode in enumerate(episodes):
				overall_index += 1
				episode_key = episode['ratingKey']
				last_viewed_at = episode.get('lastViewedAt', 0)
				episode['index'] = overall_index
				most_recent_viewed_at = max(most_recent_viewed_at, last_viewed_at)
				
				series_episodes[series_key].append({
					'ratingKey': episode_key,
					'index': overall_index,
					'type': 'tv',
					'lastViewedAt': last_viewed_at,
					'isWatched': episode_key not in unwatched_key_set,
					'title': f'{episode["parentTitle"]} Episode {str(episode["index"])} - {episode["title"]}',
					'series_title': episode['grandparentTitle']
				})
				if first_unwatched_episode is None and episode_key in unwatched_key_set:
					first_unwatched_episode = episode_key
					start_index = i
					# last_watched_time = time.strftime("%A %B %d at %I:%M %p", time.localtime(last_watched_episode["lastViewedAt"])) if last_watched_episode['lastViewedAt'] > 0 else 'not watched yet'
					# next_episode_time = time.strftime("%A %B %d at %I:%M %p", time.localtime(series_episodes[series_key][start_index]["lastViewedAt"])) if series_episodes[series_key][start_index]["lastViewedAt"] > 0 else 'not watched yet'
					# print(f'Next episode: {series_episodes[series_key][start_index]["title"]} ({next_episode_time})')
					# print(f'Last watched episode: {last_watched_episode["title"]} ({last_watched_time})')
				# else:
				# 	last_watched_episode = episode

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
				PLEX_GLOBALS['series_keys'].remove(series_key)
				del series_episodes[series_key]

		if start_index > 0 and series_episodes.get(series_key) is not None:
			series_episodes[series_key] = series_episodes[series_key][start_index:]

def build_movie_list(ssn):
	"""
	Builds the movie list for the Plex server.
	Retrieves all unwatched movies from the Plex server and sorts them by year.
	The movies are then added to the series_episodes list as if they were a TV show.
	The movies are then sorted by the date of the most recently watched movie, starting with the movie after the most recently watched movie.
	"""
	base_url = get_base_url()
	movie_section_key, _ = get_section_keys(ssn)
	series_keys, _, series_episodes = get_series_globals()

	unwatched = ssn.get(f'{base_url}/library/sections/{movie_section_key}/unwatched').json()['MediaContainer']['Metadata']
	unwatched_set = set({})
	for unwatched_item in unwatched:
		unwatched_set.add(unwatched_item['ratingKey'])

	results = ssn.get(f'{base_url}/library/sections/{movie_section_key}/all', params={})
	results.raise_for_status()
	results_json = results.json()
	movie_list = results_json['MediaContainer']['Metadata']

	movie_list = sorted(movie_list, key=lambda x: hashlib.md5(x['title'].encode()).hexdigest())
	for movie in movie_list:
		movie['index'] = movie_list.index(movie)
	
	# Track total movies for the unwatched threshold
	total_movies = len(movie_list)
	
	# Filter out movies whose slugs are in the excluded_slugs list
	filtered_movie_list = []
	for movie in movie_list:
		movie_slug = movie.get('slug', create_slug(movie['title']))
		if movie_slug in PLEX_GLOBALS['excluded_slugs']:
			continue
		filtered_movie_list.append(movie)
	
	movie_list = filtered_movie_list
	total_movies = len(movie_list)
	
	for movie in movie_list:
		if movie.get('year', 0) == 0:
			# Use existing slug or create new one
			movie_slug = movie.get('slug', create_slug(movie['title']))
			movie_config = next((item for item in PLEX_GLOBALS['metadata'] if item.get('slug') == movie_slug), {})
			if movie_config:
				movie['year'] = movie_config.get('year', 0)
				movie['slug'] = movie_config.get('slug', movie_slug)
			else:
				# Try to get the year from IMDB API
				# Use title from local config if available, otherwise use movie title
				imdb_title = movie_config.get('title', movie['title'])
				movie['year'] = get_movie_year_from_imdb(imdb_title)
				if movie['year'] == 0:
					print(f"Warning: Could not determine year for movie: {movie['title']}")

	# Check if we've reached the threshold (33% or less unwatched)
	unwatched_count = len(unwatched_set)
	if unwatched_count / total_movies <= 0.33:
		print(f"\nOnly {unwatched_count} of {total_movies} movies are unwatched ({(unwatched_count / total_movies) * 100:.1f}%)")
		print("Checking for movies to mark as unwatched...")
		
		# Go through all movies and check rewatch delays for watched ones
		for movie in movie_list:
			if movie['ratingKey'] not in unwatched_set:  # If movie is watched
				movie_slug = movie.get('slug', create_slug(movie['title']))
				movie_config = next((item for item in PLEX_GLOBALS['metadata'] if item.get('slug') == movie_slug), {})
				rewatch_delay_days = movie_config.get('rewatchDelayDays', PLEX_GLOBALS['defaultRewatchDelayDays']['movies'])
				
				last_viewed_at = movie.get('lastViewedAt', 0)
				if last_viewed_at > 0 and (time.time() - last_viewed_at) >= (rewatch_delay_days * 24 * 60 * 60):
					print(f"Marking as unwatched: {movie['title']} (last watched {time.strftime('%Y-%m-%d', time.localtime(last_viewed_at))})")
					mark_as_unwatched(ssn, movie['ratingKey'])
					unwatched_set.add(movie['ratingKey'])

	movie_list = sorted(movie_list, key=lambda x: x['year'])
	for movie in movie_list:
		movie['isWatched'] = movie['ratingKey'] not in unwatched_set
		movie['lastViewedAt'] = movie.get('lastViewedAt', 0)
		if str(movie["year"]) in movie['title']:
			movie['title'] = movie['title'].rsplit(' ', 1)[0]
		movie['title'] = f'{movie["title"]} ({str(movie["year"])})'
		movie['series_title'] = 'Movies'
		movie_slug = movie.get('slug', create_slug(movie['title']))
		key_word_parts = list(filter(lambda x: x != 'the', movie_slug.split('-')))
		
		# Check if the movie slug starts with any of the movie series slugs from PLEX_GLOBALS
		movie['key_word'] = key_word_parts[0]  # Default to first word
		
		for series_slug in PLEX_GLOBALS['movie_series_slugs']:
			if movie_slug.startswith(series_slug):
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

	print(f'\n{len(unwatched_movies)} unwatched movies')
	for movie in unwatched_movies:
		print(f'{movie["title"]}')

	print('\n--------------------------------\n')
	
	series_keys.append('movies')
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

	# Sort the the series keys by the date of the most recently watched episode
	series_keys = sorted(series_keys, key=lambda x: series_episodes[x][0].get('index', 0))

	# Build the playlist episode keys
	episode_indexes = {}
	print(f'Playlist episodes:\n')
	while len(playlist_episode_keys) < max_episodes:
		for series_key in series_keys:
			next_index = episode_indexes.get(series_key, episode_indexes.get(series_key, 0))
			if next_index >= len(series_episodes[series_key]):
				continue

			ekey = series_episodes[series_key][next_index]['ratingKey']
			playlist_episode_keys.append(ekey)
			episode_indexes[series_key] = (next_index + 1) % len(series_episodes[series_key])

			episode = series_episodes[series_key][next_index]
			print(f'{episode["series_title"]}: {episode["title"]}')


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
	Replaces the items in the current version of the playlist with the new list of episode keys.
	"""
	base_url = get_base_url()
	machine_id = get_machine_id(ssn)
	playlist_name, playlist_key, playlist_episode_keys, _ = get_playlist_globals()

	params = {'type': 'video', 'title': playlist_name, 'smart': '0', 'uri': f'server://{machine_id}/com.plexapp.plugins.library/library/metadata/{",".join(playlist_episode_keys)}'}

	if playlist_key is not None:
		ssn.delete(f'{base_url}/playlists/{playlist_key}', params=params)

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

	args = parser.parse_args()

	#call function and process result
	response = rob_tv(ssn=ssn)
	if response.status_code != 200:
		print("ERROR: Playlist could not be updated!")
		parser.error(response)

	print("Playlist updated successfully!")
