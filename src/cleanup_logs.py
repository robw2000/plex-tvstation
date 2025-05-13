#!/usr/bin/env python3

"""
Log Cleanup Script

This script cleans up the cron.log file by keeping only the last 3 days of activity.
It reads the cron.log file, filters entries from the last 3 days, and writes them back.

Requirements:
- Python 3.x
- Required Python packages:
  - os
  - time
  - pathlib

Usage:
- Run the script: python cleanup_logs.py
- The script will keep only the last 3 days of entries in cron.log
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta

def clean_cron_log(logs_dir):
	"""
	Keeps only the last 3 days of entries in cron.log file.
	For lines without timestamps, uses the last known timestamp or next known timestamp.
	"""
	cron_log = logs_dir / 'cron.log'
	if not cron_log.exists():
		return

	# Calculate timestamp for 3 days ago
	three_days_ago = datetime.now() - timedelta(days=3)
	
	# Read all lines from cron.log
	with open(cron_log, 'r') as f:
		lines = f.readlines()
	
	# First pass: collect all timestamps and their line numbers
	timestamp_map = {}  # Maps line numbers to their timestamps
	last_timestamp = None
	
	for i, line in enumerate(lines):
		try:
			# Extract timestamp from line [YYYY-MM-DD HH:MM:SS]
			timestamp_str = line[1:20]  # Extract the timestamp portion
			line_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
			timestamp_map[i] = line_time
			last_timestamp = line_time
		except (ValueError, IndexError):
			# If line doesn't have a timestamp, use the last known timestamp
			if last_timestamp is not None:
				timestamp_map[i] = last_timestamp
	
	# Second pass: for lines without timestamps, look forward for the next timestamp
	next_timestamp = None
	for i in range(len(lines) - 1, -1, -1):
		if i in timestamp_map:
			next_timestamp = timestamp_map[i]
		elif next_timestamp is not None:
			timestamp_map[i] = next_timestamp
	
	# Filter lines based on their timestamps
	recent_lines = []
	for i, line in enumerate(lines):
		line_time = timestamp_map.get(i)
		if line_time is None or line_time >= three_days_ago:
			recent_lines.append(line)
	
	# Write filtered lines back to cron.log
	with open(cron_log, 'w') as f:
		f.writelines(recent_lines)

def run_cleanup_logs(file_dir):
	"""
	Main function that orchestrates the cron.log cleanup.
	"""
	# Adjust paths to use file_location
	logs_dir = file_dir / 'logs'
	logs_dir.mkdir(exist_ok=True)
	
	# Clean up cron.log file
	clean_cron_log(logs_dir)
