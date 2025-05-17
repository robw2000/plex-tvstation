import json
import re

# Load genre mappings from file
GENRE_MAPPINGS_PATH = '/home/rob/repos/plex-tvstation/src/genre_mappings.json'
try:
	with open(GENRE_MAPPINGS_PATH, 'r') as f:
		GENRE_MAPPINGS = json.load(f)
except Exception:
	GENRE_MAPPINGS = {}


def clean_genre_string(genre):
	"""
	Cleans a genre string by:
	1. Converting to lowercase
	2. Removing all non-alphanumeric characters (except spaces)
	3. Stripping leading/trailing spaces
	4. Mapping fully spelled out genres to their short forms if present
	5. Splitting genres containing 'and' or '&' into separate genres
	"""
	if not isinstance(genre, str):
		return []

	def clean(g):
		return ''.join(c.lower() if c.isalnum() or c.isspace() else '' for c in g).strip()

	# Lowercase and keep only alphanumeric and spaces
	cleaned = clean(genre)

	# Split genres containing 'and' or '&'
	parts = re.split(r'\s*(?:and|&)\s*', cleaned)

	# Map to short form if present and clean each part
	mapped_parts = [clean(GENRE_MAPPINGS.get(part.strip(), part.strip())) for part in parts]
	return mapped_parts 