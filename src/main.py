import argparse
import sys

# Import the modules for each functionality
from media_library_analyzer import run_media_library_analyzer
from tvstation import run_tvstation
from slug_list import run_slug_list
from plex_library_report import run_plex_report
from cleanup_logs import run_cleanup_logs
from create_plex_folders import run_create_plex_folders


def main():
	parser = argparse.ArgumentParser(description='Plex TV Station Application')
	parser.add_argument('-l', '--log-only', action='store_true', help='Only write to log files, do not print to stdout')
	parser.add_argument('action', nargs='?', default='report',
		help="Action to perform: 'tvstation', 'slugs', 'report', 'analyze', 'clean-logs', 'folders'")

	args = parser.parse_args()

	if args.action == 'tvstation':
		run_tvstation(args)
	elif args.action == 'slugs':
		run_slug_list()
	elif args.action == 'report':
		run_plex_report()
	elif args.action == 'analyze':
		run_media_library_analyzer(args)
	elif args.action == 'clean-logs':
		run_cleanup_logs()
	elif args.action == 'folders':
		run_create_plex_folders(args)
	else:
		print(f"Unknown action: {args.action}")
		sys.exit(1)


if __name__ == '__main__':
	main() 