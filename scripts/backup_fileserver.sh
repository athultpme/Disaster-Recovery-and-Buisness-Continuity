#! /bin/bash

SOURCE_DIR="/mnt/fileserver"
BACKUP_BASE="/backup/files"
FILE_HOST="192.168.52.6"
RETENTION_DAYS=30
LOG_FILE="/backup/logs/fileserver_backup.log"

# Create timestamped backup directory

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE/backup_$BACKUP_DATE"

echo "[$(date)] Starting File Server Backup via rsync..." >> $LOG_FILE

# Incremental backup using rsync
# Uses hard links to previous backup for space efficiency
LATEST_BACKUP=$(ls -t "$BACKUP_BASE"/backup_* 2>/dev/null | head -1)

if [ -n "$LATEST_BACKUP" ]; then
    # Incremental backup with link-dest
    rsync -avzh \
        --delete \
        --link-dest="$LATEST_BACKUP"\
        fileserver@$FILE_HOST:/uploads/ \
        "$BACKUP_DIR/" 2>> $LOG_FILE
else
    # Full backup on first run
    rsync -avzh \
        --delete \
        fileserver@$FILE_HOST:/uploads/ \
        "$BACKUP_DIR/" 2>> $LOG_FILE
fi

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: $BACKUP_DIR" >> $LOG_FILE
    # Create symlink to latest
    rm -f "$BACKUP_BASE/latest"
    ln -s "$BACKUP_DIR" "$BACKUP_BASE/latest"
else
    echo "[$(date)] Backup FAILED! " >> $LOG_FILE
fi

# Clean old backups
find "$BACKUP_BASE" -maxdepth 1 -type d -name "backup_*" -mtime +$RETENTION_DAYS -exec  rm -rf {} \;

echo "[$(date)] Retention cleanup complete ($RETENTION_DAYS days)" >> $LOG_FILE












