#!/usr/bin/env python3
import subprocess
import random
import time
from datetime import datetime

print("================================")
print("        CHAOS MONKEY            ")
print("================================")
print(f"Start Time: {datetime.now()}")
print()

cmds = [
    ("PostgreSQL", "ssh dbserver@192.168.52.4 'sudo systemctl stop postgresql.service'"),
    ("Nginx", "ssh -o BatchMode=yes webserver@192.168.52.3 'sudo systemctl stop nginx'"),
    ("Disk", "dd if=/dev/zero of=/backup/full.disk bs=100M count=20")
]

issue, cmd = random.choice(cmds)

print(f"[🔥 Injecting Failure] {issue}")
subprocess.run(cmd, shell=True)

print("[Waiting 60 seconds for Monit detection...]")
time.sleep(60)

print("[ Disaster injected. No recovery triggered.]")



#print("[⏳ Waiting 20 seconds before detection...]")
#time.sleep(20)

#print("[🚀 Triggering DR Orchestrator]")
#subprocess.run("python3 dr_orchestrator.py", shell=True)

#print("[✔ Chaos cycle completed]")
