#!/usr/bin/env python3

"""
Log Cleanup Script

This script cleans up old log files from the logs directory.
It deletes log files that are older than 3 days to prevent accumulation of old logs.

Requirements:
- Python 3.x
- Required Python packages:
  - os
  - time
  - glob
  - pathlib

Usage:
- Run the script: python cleanup_logs.py
- The script will delete log files older than 3 days
- It will log its execution to cron.log
"""

import os
import time
import glob
from pathlib import Path

def clean_old_logs(logs_dir):
	"""
	Deletes log files that are older than 3 days.
	"""
	current_time = time.time()
	three_days_ago = current_time - (3 * 24 * 60 * 60)  # 3 days in seconds
	
	# Get all log files in the logs directory
	log_files = glob.glob(str(logs_dir / "*.log"))
	
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

def log_cron_message(script_name, args=None, logs_dir=None):
	"""
	Log a basic message to cron.log with script name and arguments.
	This is used for cron job logging.
	"""
	timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
	cron_log = logs_dir / 'cron.log'
	
	# Only include non-None arguments that were actually passed
	args_str = ' '.join(f"{k}={v}" for k, v in args.items() if v is not None) if args else ''
	message = f"[{timestamp}] Running {script_name} with args: {args_str}"
	
	with open(cron_log, 'a') as f:
		f.write(f"{message}\n")

def run_cleanup_logs(file_dir):
	"""
	Main function that orchestrates the log cleanup.
	"""
	# Adjust paths to use file_location
	logs_dir = file_dir / 'logs'
	logs_dir.mkdir(exist_ok=True)

	# Log script execution to cron.log
	log_cron_message("cleanup_logs.py", logs_dir=file_dir / 'logs')
	
	# Clean up old log files
	clean_old_logs(logs_dir)
