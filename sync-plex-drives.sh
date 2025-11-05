#!/bin/bash
SCRIPT_PATH=$(realpath "$0")
SCRIPT_DIR=$(dirname "$SCRIPT_PATH")
LOG_FILE="$SCRIPT_DIR/logs/sync-plex-drives.log"

CURRENT_TIME=$(date +%Y-%m-%d\ at\ %l:%M:%S\ %p)
touch "$LOG_FILE"
echo "$CURRENT_TIME - Starting sync" | tee -a "$LOG_FILE"
sudo rsync -avh --exclude 'hdd*.txt' --exclude 'System Volume Information' --exclude '$RECYCLE.BIN' \
    --exclude '*.tar' \
	--delete /mnt/g/ /mnt/q/ | tee -a "$LOG_FILE"
echo "$CURRENT_TIME - Sync complete" | tee -a "$LOG_FILE"
