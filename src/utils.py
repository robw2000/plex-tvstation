import json
import re

# Load genre mappings from file
GENRE_MAPPINGS_PATH = '/home/rob/repos/plex-tvstation/src/genre_mappings.json'
try:
	with open(GENRE_MAPPINGS_PATH, 'r') as f:
		GENRE_MAPPINGS = json.load(f)
except Exception:
	GENRE_MAPPINGS = {}

def clean_genre_string(genres):
	genre_string = None
	if isinstance(genres, str):
		genre_string = genres

	elif isinstance(genres, list):
		# If the list contains objects with a 'tag' field, extract the 'tag' values

		if all(isinstance(g, dict) and 'tag' in g for g in genres):
			genre_string = ','.join([g['tag'] for g in genres])

		# If the list contains strings, join them with commas
		elif all(isinstance(g, str) for g in genres):
			genre_string = ','.join(genres)
	
	# Replace 'and' or '&' with a comma
	genre_string = re.sub(r'\s*(?:and|&)\s*', ',', genre_string)

	# Remove non-alphanumeric characters except spaces and commas
	return ''.join(c.lower() if c.isalnum() or c in ' ,-' else '' for c in genre_string).strip()


def build_genres_set(genres):
	"""
	Cleans a genre input which can be a string, list of strings, or None.
	1. If None, returns an empty set.
	2. If a string, processes it by replacing 'and' or '&' with a comma, removing non-alphanumeric characters (except spaces and commas), and splitting by commas.
	3. If a list of strings, processes each string individually.
	4. Maps fully spelled out genres to their short forms if present.
	"""
	if genres is None:
		return set()


	# get cleaned comma separated genres
	genre_string = clean_genre_string(genres)

	# map genres to consistent short forms
	mapped_parts = {GENRE_MAPPINGS.get(part.strip(), part.strip()) for part in genre_string.split(',')}

	# remove empty strings
	mapped_parts = {part for part in mapped_parts if part is not None and part != ''}

	# return as a set
	return mapped_parts

def get_nested_json_value(response, keys, default={}):
	json_data = response.json()
	for key in keys:
		json_data = json_data.get(key, {})
	return json_data if json_data else default
