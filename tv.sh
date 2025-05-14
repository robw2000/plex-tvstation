#!/bin/bash

# $1 is the log-only flag (-l)

# # All media tv station
# python3 src/main.py tvstation $1

# # Comedy tv station
# python3 src/main.py tvstation -g comedy $1

# # Action tv station
# python3 src/main.py tvstation -g action $1

# # Animation tv station
# python3 src/main.py tvstation -g animation $1

# # Sci-Fi tv station
# python3 src/main.py tvstation -g sci-fi $1

# # Horror Comedy tv station
# python3 src/main.py tvstation -g horror,comedy $1

# # Mystery Comedy tv station
# python3 src/main.py tvstation -g mystery,comedy $1

# # Sci-Fi Comedy tv station
# python3 src/main.py tvstation -g sci-fi,comedy $1

# # Animation Comedy tv station
# python3 src/main.py tvstation -g animation,comedy $1

# # All media library analyzer
# python3 src/main.py analyze $1

# # Missing episodes
# python3 src/main.py report $1

# # Missing episodes
# python3 src/main.py clean $1

# Copy content to web
mkdir -p web/content

cp logs/tv-station.md web/content/tv-station.md
cp logs/library-media.md web/content/library-media.md
cp logs/missing-episodes.md web/content/missing-episodes.md

git stash
git add web/content
git commit -m "Update web content"
git push
git stash apply
