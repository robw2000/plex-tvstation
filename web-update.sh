#!/bin/bash
# Update the static website with current log data

cd "$HOME/repos/plex-tvstation" || exit 1

# Run the markdown to HTML converter
python3 src/markdown_to_html.py
