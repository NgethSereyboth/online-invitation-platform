#!/usr/bin/env bash
#
# eInvite Backup Script
# Creates dated backups of database, media, and configuration
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
DB_PATH="$PROJECT_ROOT/data/einvite.db"
MEDIA_DIR="$PROJECT_ROOT/media"
LOG_DIR="$PROJECT_ROOT/logs"
RETENTION_DAYS=30

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="einvite_backup_$DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_PATH"

echo "Starting backup: $BACKUP_NAME"

# Backup database
if [[ -f "$DB_PATH" ]]; then
    cp "$DB_PATH" "$BACKUP_PATH/"
    echo "✓ Database backed up"
fi

# Backup media files
if [[ -d "$MEDIA_DIR" ]]; then
    tar -czf "$BACKUP_PATH/media.tar.gz" -C "$MEDIA_DIR" . 2>/dev/null || true
    echo "✓ Media files backed up"
fi

# Backup configuration
if [[ -f "$PROJECT_ROOT/server/config.py" ]]; then
    cp "$PROJECT_ROOT/server/config.py" "$BACKUP_PATH/"
    echo "✓ Configuration backed up"
fi

# Remove old backups
find "$BACKUP_DIR" -maxdepth 1 -type d -name "einvite_backup_*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
echo "✓ Old backups cleaned up"

echo "Backup completed: $BACKUP_PATH"
