#! /bin/bash

BACKUP_DIR="/backup/webserver"
WEB_HOST="192.168.52.3"
RETENTION_DAYS=3
LOG_FILE="/backup/logs/webserver_backup.log"

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/nginx_config_${BACKUP_DATE}.tar.gz"

echo "[$(date)] Backing up web server configuration..." | tee -a "$LOG_FILE"

# Backup Nginx config and web root
ssh webserver@"$WEB_HOST" "sudo tar -czf - /etc/nginx /var/www" > "$BACKUP_FILE" 2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup successful: $BACKUP_FILE" | tee -a "$LOG_FILE"
else
    echo "[$(date)] Backup FAILED" | tee -a "$LOG_FILE"
    exit 1
fi

# Clean old backups
find $BACKUP_DIR -name "nginx_config_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Complete" | tee -a "$LOG_FILE"

