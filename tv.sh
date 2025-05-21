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

# Franchise tv stations

# Star Wars tv station
python3 src/main.py tvstation -f star-wars $1

# Star Trek tv station
python3 src/main.py tvstation -f star-trek $1

# Marvel tv station
python3 src/main.py tvstation -f marvel $1

# DC tv station
python3 src/main.py tvstation -f dc $1


