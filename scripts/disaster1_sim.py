#!/usr/bin/env python3
import subprocess
import random
from datetime import datetime

print(" CHAOS MONKEY")
print("===============")
print(datetime.now())

# Simple disasters (no complex quotes)
cmds = [
    "ssh -t dbserver@192.168.52.4 sudo systemctl stop postgresql",
    "ssh -t webserver@192.168.52.3 sudo systemctl stop nginx.service",
    "dd if=/dev/zero of=/backup/full.disk bs=100M count=20"
]

cmd = random.choice(cmds)
print("Injecting:", cmd[:50]+"...")

subprocess.run(cmd, shell=True)
print("  DISASTER INJECTED")
print("  Wait 30s for alerts...")
print("\n RECOVER:")
print("python3 dr_orchestrator.py")
