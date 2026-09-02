#!/usr/bin/env python3
"""
Usage:
  python3 disaster_sim143.py             # picks one at random, as before
  python3 disaster_sim143.py disk        # inject a specific disaster by name
  python3 disaster_sim143.py postgresql
  python3 disaster_sim143.py nginx
  python3 disaster_sim143.py --list      # show available disaster names
"""

import subprocess
import random
import sys
import time
from datetime import datetime

WAIT_SECONDS = 60
LOG_FILE = "/backup/logs/disaster_sim.log"

DISASTERS = [
    {
        "name": "PostgreSQL",
        "command": [
            "ssh", "-o", "BatchMode=yes", "dbserver@192.168.52.4",
            "sudo systemctl stop postgresql.service"
        ]
    },
    {
        "name": "Nginx",
        "command": [
            "ssh", "-o", "BatchMode=yes", "webserver@192.168.52.3",
            "sudo systemctl stop nginx.service"
        ]
    },
    {
        "name": "Disk",
        "command": [
            "bash", "-lc",
            "dd if=/dev/zero of=/backup/full.disk bs=100M count=20 status=none"
        ]
    }
]


def log_event(message):
    entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


def inject_disaster(disaster):
    log_event("================================")
    log_event("CHAOS MONKEY / DISASTER SIMULATOR")
    log_event("================================")
    log_event(f"[START] Injecting failure: {disaster['name']}")

    try:
        result = subprocess.run(
            disaster["command"], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log_event(f"[SUCCESS] Failure injected: {disaster['name']}")
        else:
            log_event(f"[ERROR] Injection failed: {disaster['name']}")
            if result.stdout.strip():
                log_event(f"[STDOUT] {result.stdout.strip()}")
            if result.stderr.strip():
                log_event(f"[STDERR] {result.stderr.strip()}")
            return False
    except Exception as e:
        log_event(f"[EXCEPTION] {disaster['name']} injection error: {e}")
        return False

    log_event(f"[WAIT] Waiting {WAIT_SECONDS} seconds for monitoring detection")
    time.sleep(WAIT_SECONDS)
    log_event("[DONE] Disaster injected successfully. No automatic trigger from this script.")
    return True


def find_disaster(name):
    name = name.strip().lower()
    for d in DISASTERS:
        if d["name"].lower() == name:
            return d
    return None


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return

    if args and args[0] == "--list":
        print("Available disasters:")
        for d in DISASTERS:
            print(f"  {d['name']}")
        return

    if args:
        disaster = find_disaster(args[0])
        if disaster is None:
            print(f"Unknown disaster: '{args[0]}'")
            print("Available disasters:", ", ".join(d["name"] for d in DISASTERS))
            sys.exit(1)
    else:
        disaster = random.choice(DISASTERS)
        log_event(f"[INFO] No disaster specified, picked at random: {disaster['name']}")

    inject_disaster(disaster)


if __name__ == "__main__":
    main()
