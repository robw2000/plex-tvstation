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
	When all episodes of a series are watched, the series is then excluded from the playlist until the most recent viewedAt time is more than 90 days ago.
	Only unwatched movies and episodes are included in the playlist.

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
		excluded_slugs: A comma-delimited list of slugs that will be excluded from the playlist.

	Run the script at an interval to regularly update the playlist.
"""
from os import getenv
import time
import hashlib
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get excluded_slugs from environment variable and convert to array
excluded_slugs_str = getenv('excluded_slugs', '')
excluded_slugs = [slug.strip() for slug in excluded_slugs_str.split(',')] if excluded_slugs_str else []

# Load missing metadata from JSON file
try:
	with open('missing_metadata.json', 'r') as f:
		MISSING_METADATA = json.load(f)
except FileNotFoundError:
	MISSING_METADATA = {}

PLEX_GLOBALS = {
	'playlist_name': getenv('playlist_name', 'My Favs TV'),
	'plex_ip': getenv('plex_ip', '192.168.1.196'),
	'plex_port': getenv('plex_port', '32400'),
	'plex_api_token': getenv('plex_api_token', ''),
	'user_id': getenv('user_id', '1'),
	'max_episodes': int(getenv('max_episodes', 50)),
	'excluded_slugs': excluded_slugs,

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
		if s['slug'] in PLEX_GLOBALS['excluded_slugs']:
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
			season_key = season["ratingKey"]

			unwatched_response = ssn.get(f'{base_url}/library/metadata/{season_key}/children?unwatched=1')
			unwatched = unwatched_response.json().get('MediaContainer', {}).get('Metadata', [])
			unwatched_key_set = set([x['ratingKey'] for x in unwatched])

			episodes = ssn.get(f'{base_url}/library/metadata/{season_key}/children', params={}).json()['MediaContainer']['Metadata']
			for episode in episodes:
				episode_key = episode['ratingKey']
				last_viewed_at = episode.get('lastViewedAt', 0)
								
				most_recent_viewed_at = max(most_recent_viewed_at, last_viewed_at)
				
				series_episodes[series_key].append({
					'ratingKey': episode_key,
					'type': 'tv',
					'lastViewedAt': last_viewed_at,
					'isWatched': episode_key not in unwatched_key_set,
					'title': f'{episode["parentTitle"]} Episode {str(episode["index"])} - {episode["title"]}',
					'series_title': episode['grandparentTitle']
				})
				if first_unwatched_episode is None and episode_key in unwatched_key_set:
					first_unwatched_episode = episode_key
					start_index = len(series_episodes[series_key]) - 1

		# If all episodes are watched, mark them as unwatched
		all_watched = first_unwatched_episode is None
		if all_watched and (time.time() - most_recent_viewed_at) >= (90 * 24 * 60 * 60):  # 90 days in seconds
			mark_as_unwatched(ssn, series_key)

		if start_index > 0:
			series_episodes[series_key] = series_episodes[series_key][start_index:] + series_episodes[series_key][:start_index]

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
	for movie in movie_list:
		if movie.get('year', 0) == 0 and movie['title'] not in MISSING_METADATA:
			print(f"Error: Movie with no year: {movie['title']}")
			exit(1)
		elif movie.get('year', 0) == 0:
			movie['year'] = MISSING_METADATA[movie['title']]['year']
			movie['slug'] = MISSING_METADATA[movie['title']]['slug']

	movie_list = sorted(movie_list, key=lambda x: x['year'])
	for movie in movie_list:
		movie['isWatched'] = movie['ratingKey'] not in unwatched_set
		movie['lastViewedAt'] = movie.get('lastViewedAt', 0)
		movie['title'] = f'{movie["title"]} ({str(movie["year"])})'
		movie['series_title'] = 'Movies'
		key_word_parts = list(filter(lambda x: x != 'the', movie['slug'].split('-')))
		movie['key_word'] = key_word_parts[0] if key_word_parts[0] != 'star' else f'{key_word_parts[0]} {key_word_parts[1]}'

	# Sort the movies by a hash of the title which will randomize the sort but also ensure the sort is the same each time
	unwatched_movies = list(filter(lambda x: not x['isWatched'], movie_list))
	unwatched_movies.sort(key=lambda x: hashlib.md5(x.get('title', '').encode()).hexdigest())

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
	
	movie_list = unwatched_movies + list(filter(lambda x: x['isWatched'], movie_list))

	series_keys.append('movies')
	series_episodes['movies'] = movie_list

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
	series_keys = sorted(series_keys, key=lambda x: series_episodes[x][-1]['lastViewedAt'])

	# Keep the most recently viewed series first but shuffle the other series order
	first_series_key = series_keys[0]
	remainder_series_keys = sorted(series_keys[1:])
	next_key_index = find_index(remainder_series_keys, lambda x: x > first_series_key)
	series_keys = [first_series_key] + remainder_series_keys[next_key_index:] + remainder_series_keys[:next_key_index]

	# Build the playlist episode keys
	episode_indexes = {}
	print(f'Playlist episodes:\n')
	while len(playlist_episode_keys) < max_episodes:
		for series_key in series_keys:
			next_index = episode_indexes.get(series_key, episode_indexes.get(series_key, 0))
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
