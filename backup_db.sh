#!/bin/bash
# backup_db.sh — Daily backup of ptool Railway Postgres → Dropbox
# Scheduled via cron to run nightly at 2am.
# Keeps 30 days of backups, then auto-deletes older ones.
#
# Requires: brew install libpq
# First run: chmod +x backup_db.sh

set -e

PTOOL_DIR="$HOME/pythonprojects/ptool"
BACKUP_DIR="$HOME/Library/CloudStorage/Dropbox/LogoIncluded/DB Backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ptool_backup_$TIMESTAMP.sql.gz"
KEEP_DAYS=30
LOG="$HOME/Library/Logs/ptool_backup.log"

# pg_dump from Homebrew libpq
PG_DUMP="/opt/homebrew/opt/libpq/bin/pg_dump"

echo "----------------------------------------" >> "$LOG"
echo "$(date '+%Y-%m-%d %H:%M:%S') Starting backup..." >> "$LOG"

# Load DATABASE_URL from .env
export $(grep '^DATABASE_URL' "$PTOOL_DIR/.env" | tr -d '"')

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Dump and compress
$PG_DUMP "$DATABASE_URL" | gzip > "$BACKUP_FILE"

echo "$(date '+%Y-%m-%d %H:%M:%S') ✓ Saved: $BACKUP_FILE" >> "$LOG"

# Remove backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "ptool_backup_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "$(date '+%Y-%m-%d %H:%M:%S') ✓ Done. Backups older than $KEEP_DAYS days removed." >> "$LOG"
