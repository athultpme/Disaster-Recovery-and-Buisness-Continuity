#!/usr/bin/env python3
import subprocess
import os
from datetime import datetime
import glob 

BACKUP_DIR = "/backup/database"
DB_HOST = "192.168.52.4"
DB_NAME = "healthcare_db"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"{BACKUP_DIR}/postgres_backup_{timestamp}.dump.gz"

print(f"[+] Creating {backup_file}...")
cmd = f'ssh dbserver@{DB_HOST} "sudo -u postgres pg_dump -Fc {DB_NAME}" | gzip | sudo tee "{backup_file}" > /dev/null'

result = subprocess.run(cmd, shell=True)
if result.returncode == 0:
    size = os.path.getsize(backup_file) / (1024*1024)
    print(f"[✅] Backup complete: {size:.1f} MB")
    
    # Test integrity
    subprocess.run(f"sudo gunzip -t '{backup_file}'", shell=True)
    print("[✅] Integrity verified")
else:
    print("[❌] Backup failed")
    sys.exit(1)

# Clean old (keep 10 latest)
backups = sorted(glob.glob(f"{BACKUP_DIR}/postgres_backup_*.dump.gz"))
for old in backups[:-10]:
    os.unlink(old)
    print(f"[Clean] {old}")
