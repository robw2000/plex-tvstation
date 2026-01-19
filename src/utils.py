import json
import re
import socket
import requests
import sys

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

def get_local_ip():
	"""
	Get the local IP address of this computer.
	Returns the IP address as a string, or None if it cannot be determined.
	"""
	try:
		# Connect to a remote address to determine the local IP
		# This doesn't actually send data, just determines which interface would be used
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.settimeout(0)
		try:
			# Connect to a non-routable address (doesn't actually connect)
			s.connect(('8.8.8.8', 80))
			ip = s.getsockname()[0]
		except Exception:
			ip = None
		finally:
			s.close()
		return ip
	except Exception:
		return None

def test_plex_connectivity_with_fallback(ssn, plex_globals):
	"""
	Tests connectivity to the Plex server with IP fallback.
	First tries the configured plex_ip, then falls back to the local IP address.
	Updates plex_globals['plex_ip'] if fallback is used.
	Raises a ConnectionError and exits if both attempts fail.
	
	Args:
		ssn: The requests session object
		plex_globals: Dictionary containing 'plex_ip', 'plex_port', and 'base_url'
	
	Returns:
		True if connection succeeds
	"""
	plex_port = plex_globals['plex_port']
	configured_ip = plex_globals['plex_ip']
	
	# Build base URL from configured IP
	base_url = f"http://{configured_ip}:{plex_port}"
	
	# First, try the configured IP
	try:
		response = ssn.get(f'{base_url}/', timeout=5)
		response.raise_for_status()
		plex_globals['base_url'] = base_url
		return True
	except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
		# If configured IP fails, try local IP
		local_ip = get_local_ip()
		if local_ip and local_ip != configured_ip:
			# Update the IP and try again
			plex_globals['plex_ip'] = local_ip
			base_url = f"http://{local_ip}:{plex_port}"
			
			try:
				response = ssn.get(f'{base_url}/', timeout=5)
				response.raise_for_status()
				plex_globals['base_url'] = base_url
				# Success with local IP
				return True
			except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e2:
				# Both attempts failed
				error_msg = f"""
ERROR: Cannot connect to Plex server.

Attempted connections:
1. Configured IP ({configured_ip}:{plex_port}) - FAILED
2. Local IP ({local_ip}:{plex_port}) - FAILED

This is a network connectivity issue. Please check:

1. Is the Plex server running?
   - Check if the Plex server is powered on and running
   - Verify the Plex service is active on the server

2. Network connectivity:
   - Are you on the same network as the Plex server?
   - Can you ping the server? Try: ping {local_ip}
   - Can you access the Plex web interface at http://{local_ip}:{plex_port}?

3. Firewall issues:
   - Check if a firewall is blocking port {plex_port}
   - Verify the Plex server firewall allows connections on port {plex_port}

4. VPN/Network changes:
   - If using WSL2, ensure your network configuration allows access to local network
   - Check if VPN or network changes have affected connectivity

Original errors:
- Configured IP: {str(e)}
- Local IP: {str(e2)}
"""
				print(error_msg, file=sys.stderr)
				sys.exit(1)
		else:
			# No local IP available or same as configured, just report the original error
			error_msg = f"""
ERROR: Cannot connect to Plex server at {configured_ip}:{plex_port}

This is a network connectivity issue. Please check:

1. Is the Plex server running?
   - Check if the Plex server is powered on and running
   - Verify the Plex service is active on the server

2. Has the IP address changed?
   - The configured IP is: {configured_ip}
   - Check if your Plex server has a new IP address
   - You can set the correct IP using: export plex_ip=<new_ip>
   - Or create a .env file with: plex_ip=<new_ip>

3. Network connectivity:
   - Are you on the same network as the Plex server?
   - Can you ping the server? Try: ping {configured_ip}
   - Can you access the Plex web interface at http://{configured_ip}:{plex_port}?

4. Firewall issues:
   - Check if a firewall is blocking port {plex_port}
   - Verify the Plex server firewall allows connections on port {plex_port}

5. VPN/Network changes:
   - If using WSL2, ensure your network configuration allows access to local network
   - Check if VPN or network changes have affected connectivity

Original error: {str(e)}
"""
			print(error_msg, file=sys.stderr)
			sys.exit(1)
