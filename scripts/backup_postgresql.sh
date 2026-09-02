#!/bin/bash

BACKUP_DIR="/backup/database"
DB_USER="postgres"
DB_HOST="192.168.52.4"
RETENTION_DAYS=1
LOG_FILE="/backup/logs/postgres_backup.log"

# Create Timestamp
BACKUP_DATE=$(date +%Y%m%d_%H%m%S)
BACKUP_FILE="$BACKUP_DIR/postgres_backup_$BACKUP_DATE.dump"

echo "[$(date)] Starting PostgreSQL backup..." >> $LOG_FILE

#Full backup (compress with gzip)

#pg_dump -h $DB_HOST -U postgres -F c > "$BACKUP_FILE" 2>> $LOG_FILE

PGPASSWORD='backup123' pg_dump -h $DB_HOST -U postgres -F c | gzip > "$BACKUP_FILE" 2>> $LOG_FILE

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: $BACKUP_FILE" >> $LOG_FILE
    # Compress further
    gzip "$BACKUP_FILE"
else
    echo "[$(date)] Backup FAILED!" >> $LOG_FILE
    exit 1
fi

#Clean old backups (older than 7 days)
find $BACKUP_DIR -name "postgrs_backup_*.dump.gz" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Cleanup complete. Retention set to $RETENTION_DAYS days" >> $LOG_FILE
























