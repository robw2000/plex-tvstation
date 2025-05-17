import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Import the modules for each functionality
from media_library_analyzer import run_media_library_analyzer
from tvstation import run_tvstation
from slug_list import run_slug_list
from plex_library_report import run_plex_report
from cleanup_logs import run_cleanup_logs
from create_plex_folders import run_create_plex_folders

# Load environment variables
load_dotenv()

def main():
	parser = argparse.ArgumentParser(description='Plex TV Station Application')
	parser.add_argument('-l', '--log-only', action='store_true', help='Only write to log files, do not print to stdout')
	parser.add_argument('-f', '--file-dir', default=Path(__file__).parent.parent.absolute(),
		help='The base file location for logs and configuration files')
	parser.add_argument('-g', '--genres', default='comedy,Science Fiction & Fantasy', help='Comma-separated list of genres to filter by')
	parser.add_argument('action', nargs='?', default='tvstation',
		help="Action to perform: 'tvstation', 'slugs', 'report', 'analyze', 'clean', 'folders'")
	parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode for folder creation')

	args = parser.parse_args()

	file_dir = Path(args.file_dir)
	
	if args.action == 'tvstation':
		run_tvstation(args, file_dir)
	elif args.action == 'slugs':
		run_slug_list(file_dir)
	elif args.action == 'report':
		run_plex_report(file_dir)
	elif args.action == 'analyze':
		run_media_library_analyzer(args, file_dir)
	elif args.action == 'clean':
		run_cleanup_logs(file_dir)
	elif args.action == 'folders':
		run_create_plex_folders(args, file_dir)
	else:
		print(f"Unknown action: {args.action}")
		sys.exit(1)


if __name__ == '__main__':
	main()