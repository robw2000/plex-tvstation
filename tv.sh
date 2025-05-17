#!/bin/bash

# $1 is the log-only flag (-l)

# All media tv station
python3 src/main.py tvstation $1

# Comedy tv station
python3 src/main.py tvstation -g comedy $1

# Action tv station
python3 src/main.py tvstation -g action $1

# Animation tv station
python3 src/main.py tvstation -g animation $1

# Sci-Fi tv station
python3 src/main.py tvstation -g sci-fi $1

# Fantasy tv station
python3 src/main.py tvstation -g fantasy $1

# All media library analyzer
python3 src/main.py analyze $1

# Missing episodes
python3 src/main.py report $1

# Missing episodes
python3 src/main.py clean $1

