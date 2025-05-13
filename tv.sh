#!/bin/bash

# $1 is the log-only flag (-l)
python3 src/main.py tvstation $1

mkdir -p web/content

cp logs/tv-station.md web/content/tv-station.md
cp logs/library-media.md web/content/library-media.md
cp logs/missing-episodes.md web/content/missing-episodes.md
