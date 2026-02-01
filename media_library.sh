#!/bin/bash

# Wrapper to generate the Plex media library report.
# All arguments are passed through to the Python entrypoint.
# Common flags:
#   -l, --log-only  Only write to log files, do not print to stdout
#   --force         Force regeneration, ignoring freshness checks

python3 src/main.py medialibrary "$@"
