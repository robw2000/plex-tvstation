#!/bin/bash
SCRIPT_PATH=$(realpath "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
LOG_FILE="$SCRIPT_DIR/logs/sync-plex-drives.log"

CURRENT_TIME=$(date +%Y-%m-%d\ at\ %l:%M:%S\ %p)
touch "$LOG_FILE"
echo "$CURRENT_TIME - Starting sync" | tee -a "$LOG_FILE"
rsync -avh --exclude 'hdd*.txt' --exclude 'System Volume Information' /mnt/g/ /mnt/p/ | tee -a "$LOG_FILE"
echo "$CURRENT_TIME - Sync complete" | tee -a "$LOG_FILE"
