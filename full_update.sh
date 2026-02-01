#!/bin/bash

# Full update script that runs all update scripts in order
# $1 is the log-only flag (-l) that will be passed to scripts that support it

set -e  # Exit on error

echo "Starting full update..."

# Run TV station updates
echo "Running TV station updates..."
./tv.sh "$1"

# Generate media library report
echo "Generating media library report..."
./media_library.sh "$@"

# Analyze missing media
echo "Analyzing missing media..."
./missing_media.sh "$@"

# Update web pages
echo "Updating web pages..."
./web_update.sh

echo "Full update complete!"
