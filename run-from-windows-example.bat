@echo off
wsl -e bash -lic "cd /home/myuser/repos/plex-tvstation && source ./plexenv/bin/activate && python tvstation.py"