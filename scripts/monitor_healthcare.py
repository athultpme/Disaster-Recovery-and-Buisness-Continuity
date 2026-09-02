#!/usr/bin/env python3
import subprocess
import time
import os

def log(msg):
    with open('/var/log/healthcare_monitor.log', 'a') as f:
        f.write(f"{time.ctime()}: {msg}\n")

while True:
    try:
        # Check backup file
        if os.path.getsize('/backup/database/postgres_backup_latest.gz') < 1024*1024:
            log("ALERT: Backup too small!")
        else:
            log("OK: Backup healthy")
        
        # Check DB port (nc test)
        if subprocess.call("nc -z 192.168.52.4 5432", shell=True, timeout=5) != 0:
            log("ALERT: DB 5432 down!")
        else:
            log("OK: DB alive")
            
    except Exception as e:
        log(f"ERROR: {e}")
    
    time.sleep(300)  # 5 minutes
