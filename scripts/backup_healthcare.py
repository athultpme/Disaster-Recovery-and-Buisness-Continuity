#!/usr/bin/env python3
import subprocess, time
while True:
    subprocess.run("pg_dump healthcare_db | gzip > /backup/database/postgres_backup_$(date +%s).gz", shell=True)
    time.sleep(300)  # 5min
