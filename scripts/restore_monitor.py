#!/usr/bin/env python3
import subprocess
import os
import tempfile
import sys

BACKUP_DIR = "/backup/database"
DB_HOST = "192.168.52.4"
DB_NAME = "healthcare_db"

# Find latest
latest = subprocess.check_output(f"ls -t {BACKUP_DIR}/postgres_backup_*.dump.gz | head -n1", shell=True).decode().strip()
print(f"[+] Using {latest}")

# Test integrity
subprocess.run(f"sudo gunzip -t '{latest}'", shell=True, check=True)
print("[+] Integrity OK")

# Detect format
with tempfile.NamedTemporaryFile() as tmp:
    subprocess.run(f"sudo gunzip -c '{latest}' | head -c 100 > '{tmp.name}'", shell=True, check=True)
    with open(tmp.name, 'rb') as f:
        magic = f.read(6)

if magic.startswith(b'PGDMP'):
    print("[+] Custom (-Fc) → pg_restore")
    restore_cmd = f"sudo gunzip -c '{latest}' | ssh dbserver@{DB_HOST} 'sudo -u postgres pg_restore -d {DB_NAME} --clean --if-exists --verbose'"
else:
    print("[+] Plain SQL → psql")
    restore_cmd = f"sudo gunzip -c '{latest}' | ssh dbserver@{DB_HOST} 'sudo -u postgres psql -d {DB_NAME}'"

print("[+] Restoring...")
subprocess.run(restore_cmd, shell=True, check=True)
print("[✅] Restore complete")

# Verify
count = subprocess.check_output(f"ssh dbserver@{DB_HOST} 'sudo -u postgres psql -d {DB_NAME} -t -c \"SELECT COUNT(*) FROM pg_tables;\"'", shell=True).decode().strip()
print(f"[INFO] Tables: {count}")
