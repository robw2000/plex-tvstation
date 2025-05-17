import json
import re

# Load genre mappings from file
GENRE_MAPPINGS_PATH = '/home/rob/repos/plex-tvstation/src/genre_mappings.json'
try:
	with open(GENRE_MAPPINGS_PATH, 'r') as f:
		GENRE_MAPPINGS = json.load(f)
except Exception:
	GENRE_MAPPINGS = {}


def clean_genres(genre):
	"""
	Cleans a genre input which can be a string, list of strings, or None.
	1. If None, returns an empty list.
	2. If a string, processes it by replacing 'and' or '&' with a comma, removing non-alphanumeric characters (except spaces and commas), and splitting by commas.
	3. If a list of strings, processes each string individually.
	4. Maps fully spelled out genres to their short forms if present.
	"""
	if genre is None:
		return []

	def clean(g):
		# Replace 'and' or '&' with a comma
		g = re.sub(r'\s*(?:and|&)\s*', ',', g)
		# Remove non-alphanumeric characters except spaces and commas
		return ''.join(c.lower() if c.isalnum() or c.isspace() or c == ',' else '' for c in g).strip()

	if isinstance(genre, str):
		# Clean the genre string
		cleaned_genre = clean(genre)
		# Split by commas
		parts = cleaned_genre.split(',')
	elif isinstance(genre, list):
		# If the list contains objects with a 'tag' field, extract the 'tag' values
		if all(isinstance(g, dict) and 'tag' in g for g in genre):
			parts = [clean(g['tag']) for g in genre]
		else:
			# Clean each genre in the list
			parts = [clean(g) for g in genre]
	else:
		return []

	# Map to short form if present and clean each part
	mapped_parts = [clean(GENRE_MAPPINGS.get(part.strip(), part.strip())) for part in parts]
	return mapped_parts
