#!/usr/bin/env python3
"""
Extends dr_orchestrator143.py with:
  1. Per-host disk checks over SSH (matches what your latest log actually
     runs), instead of only checking the local /backup via psutil.
  2. Classification of SSH failures so "permission denied" (broken key
     trust) is never reported as "low disk space" again.
  3. An escalation tier: if the normal recover_disk.yml still hasn't
     fixed things after VERIFY_RETRIES, automatically run
     recover_disk_emergency.yml once before giving up.

NOTE: your production orchestrator (the one that produced the
per-host disk log) already differs from dr_orchestrator143.py — please
share that exact file if you want a precise patch instead of this
rebuild. This version is based on dr_orchestrator143.py's structure.
"""

import os
import subprocess
import time
from datetime import datetime

LOG_FILE = "/backup/logs/dr_alerts.log"
INVENTORY = "/backup/scripts/ansible/inventory.ini"
PLAYBOOK_DIR = "/backup/scripts/ansible"
MIN_FREE_BYTES = 1 * 1024**3  # 1 GB
VERIFY_RETRIES = 3
VERIFY_DELAY = 5

# (label, ssh_target, mount_path)
DISK_TARGETS = [
    ("web", "webserver@192.168.52.3", "/"),
    ("db", "dbserver@192.168.52.4", "/"),
    ("file", "fileserver@192.168.52.6", "/"),
    ("backup", "backupserver@192.168.52.5", "/backup"),
]

PLAYBOOKS = {
    "PostgreSQL": "recover_postgres.yml",
    "Nginx": "recover_nginx.yml",
    "FileServer": "recover_fileserver.yml",
    "BackupServer": "recover_backupserver.yml",
    "Disk": "recover_disk.yml",
}

# Escalation tier: only used for issues that still fail after the normal
# playbook + verify retries have already been tried.
EMERGENCY_PLAYBOOKS = {
    "Disk": "recover_disk_emergency.yml",
}


def ensure_log_dir():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log_event(message):
    ensure_log_dir()
    entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


def run_command(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)


def ssh_command(host, remote_cmd, timeout=20):
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no", host, remote_cmd,
    ]
    return run_command(cmd, timeout=timeout)


def classify_ssh_failure(stderr_text):
    """Tell auth failures apart from network/service failures so they
    never get silently reported as 'low disk space'."""
    text = stderr_text.lower()
    if "permission denied" in text:
        return "SSH_AUTH_FAILURE"
    if "timed out" in text or "connection refused" in text or "no route to host" in text:
        return "SSH_UNREACHABLE"
    return "SSH_ERROR"


def check_disk_all_hosts():
    """Returns (all_healthy: bool, problems: list[str])."""
    problems = []
    for label, host, mount in DISK_TARGETS:
        code, out, err = ssh_command(
            host, f"df -B1 --output=avail,target {mount} | tail -n 1"
        )
        if code != 0:
            kind = classify_ssh_failure(err)
            log_event(f"[ERROR] Disk check failed on {label} ({host}), mount={mount}: {kind}: {err}")
            problems.append(f"{label}:{mount} ({kind})")
            continue
        try:
            avail_bytes = int(out.split()[0])
        except (ValueError, IndexError):
            log_event(f"[ERROR] Could not parse disk output for {label}: '{out}'")
            problems.append(f"{label}:{mount} (PARSE_ERROR)")
            continue

        free_gb = avail_bytes / (1024**3)
        log_event(f"[DEBUG] {label} ({host}) {mount} free space: {free_gb:.2f} GB")
        if avail_bytes < MIN_FREE_BYTES:
            problems.append(f"{label}:{mount}")

    if problems:
        log_event(f"[ALERT] Low disk space or disk check failed on: {', '.join(problems)}")
    return len(problems) == 0, problems


def run_ansible_playbook(playbook_name):
    playbook_path = os.path.join(PLAYBOOK_DIR, playbook_name)
    cmd = ["ansible-playbook", "-i", INVENTORY, playbook_path]
    log_event(f"[INFO] Running playbook: {playbook_path}")
    code, out, err = run_command(cmd, timeout=300)
    if out:
        log_event(out)
    if err:
        log_event(err)
    return code == 0


def orchestrate_recovery(issues):
    start_time = time.time()

    for issue in issues:
        log_event(f"[ALERT] {issue} failure detected")
        playbook = PLAYBOOKS.get(issue)
        if playbook:
            log_event(f"[RECOVERY] {issue} recovery started")
            run_ansible_playbook(playbook)

    healthy = False
    remaining = issues
    for attempt in range(1, VERIFY_RETRIES + 1):
        log_event(f"[VERIFY] Recovery validation attempt {attempt}/{VERIFY_RETRIES}")
        time.sleep(VERIFY_DELAY)
        disk_ok, disk_problems = check_disk_all_hosts()
        healthy = disk_ok
        remaining = ["Disk"] if disk_problems else []
        if healthy:
            rto = round(time.time() - start_time, 2)
            log_event(f"[SUCCESS] System recovered successfully in {rto} seconds")
            log_event(f"[NOTIFY] Recovery complete | RTO={rto}s")
            return True
        log_event(f"[VERIFY] Still unhealthy: {', '.join(remaining)}")

    # Escalation: normal playbook + retries didn't fix it. Try the
    # emergency playbook once before declaring failure, instead of
    # stopping here as the old orchestrator did.
    for issue in remaining:
        emergency_playbook = EMERGENCY_PLAYBOOKS.get(issue)
        if not emergency_playbook:
            continue
        log_event(f"[ESCALATION] Standard recovery insufficient for {issue}, running emergency playbook")
        run_ansible_playbook(emergency_playbook)
        time.sleep(VERIFY_DELAY)
        disk_ok, disk_problems = check_disk_all_hosts()
        if disk_ok:
            rto = round(time.time() - start_time, 2)
            log_event(f"[SUCCESS] System recovered via escalation in {rto} seconds")
            log_event(f"[NOTIFY] Recovery complete (escalated) | RTO={rto}s")
            return True

    log_event("[CRITICAL] Recovery failed after retries and escalation")
    log_event(f"[NOTIFY] Recovery FAILED: {', '.join(remaining)}")
    return False


def main():
    log_event("------------------------------------------------")
    log_event("[DR CHECK STARTED]")

    disk_ok, disk_problems = check_disk_all_hosts()
    issues = ["Disk"] if not disk_ok else []

    if not issues:
        log_event("[STATUS] All systems healthy")
        log_event("[NOTIFY] System healthy")
    else:
        log_event(f"[ALERT] Issues found: {', '.join(issues)}")
        orchestrate_recovery(issues)

    log_event("[DR CHECK FINISHED]")


if __name__ == "__main__":
    main()
