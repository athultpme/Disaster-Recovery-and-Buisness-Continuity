#!/usr/bin/env python3
import subprocess
import os

BACKUP_DIR =  "/backup/files/latest"
DESTINATION = "fileserver@192.168.52.6:/uploads/"
SERVICE = "smbd"


def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

print("[+] Starting File Server Recovery")

#Stop Samba service
run(f"systemctl stop {SERVICE}")

#Restore files
run(f"rsync -avzh {BACKUP_DIR} {DESTINATION}")


#Restart service
run(f"systemctl start {SERVICE}")

print(" File Server recovery completed successfully")




