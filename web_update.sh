#!/bin/bash
# Update the static website with current log data

set -e  # Exit on error

cd "$HOME/repos/plex-tvstation" || exit 1

# Run the markdown to HTML converter
python3 src/markdown_to_html.py

# Ensure we're on the main branch
git checkout main

# Check if there are any changes in the web/ or cache/ folders
if git diff --quiet --exit-code web/ cache/; then
	# No changes, exit silently
	exit 0
fi

# Stage all changes in the web/ and cache/ folders
git add web/ cache/

# Create a commit with a timestamp
COMMIT_MSG="Update web files - $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MSG"

# Push to main branch
git push origin main
