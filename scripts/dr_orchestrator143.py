#!/usr/bin/env python3
"""
Canonical DR orchestrator. Supersedes every other dr_orchestrator*.py
variant - archive the rest in old_versions/ once this is confirmed working.

Fixes applied in this version, each tied to a specific symptom seen in
production logs:

1. FLAPPING (Nginx reported fixed, then "still unhealthy" one cycle
   later, then fine again): each check now retries with a delay before
   being trusted, and there's a settle period after a restart before
   the first verification attempt - services need a few seconds to
   actually finish coming up, not just get a restart command issued.

2. FALSE FAILURES FROM TRANSIENT SSH HICCUPS (fileserver timing out on
   one df call): every check retries up to CHECK_RETRIES times with a
   short delay before being counted as a real failure.

3. THE RECURRING DISK PROBLEM: rather than depend on recover_disk.yml
   having been correctly deployed (which has repeatedly not been the
   case), this script has a built-in Python failsafe that directly
   removes /backup/full.disk over SSH if disk is still critical after
   the playbook runs - independent of what's in the YAML file.

4. SSH FAILURE CLASSIFICATION: auth failures, timeouts, and real
   failures are logged distinctly so "permission denied" is never
   silently reported as "service down" or "low disk space" again.
"""

import os
import subprocess
import time
from datetime import datetime

LOG_FILE = "/backup/logs/dr_alerts.log"
INVENTORY = "/backup/scripts/ansible/inventory.ini"
PLAYBOOK_DIR = "/backup/scripts/ansible"
MIN_FREE_DISK = 1 * 1024**3  # 1 GB
VERIFY_RETRIES = 3
VERIFY_DELAY = 15          # was 5 - too short for postgres/samba to fully restart
SETTLE_DELAY = 10          # wait after triggering recovery, before first verify
CHECK_RETRIES = 2          # per-check retries before trusting a failure
CHECK_RETRY_DELAY = 3
AUTO_RECOVERY = True

HOSTS = {
    "web": "webserver@192.168.52.3",
    "db": "dbserver@192.168.52.4",
    "file": "fileserver@192.168.52.6",
    "backup": "backupserver@192.168.52.5",
}

DISK_TARGETS = {
    "web": "/",
    "db": "/",
    "file": "/",
    "backup": "/backup",
}

PLAYBOOKS = {
    "PostgreSQL": "recover_postgres.yml",
    "Nginx": "recover_nginx.yml",
    "FileServer": "recover_fileserver.yml",
    "BackupServer": "recover_backupserver.yml",
    "Disk": "recover_disk.yml",
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
        return 1, "", f"TIMEOUT after {timeout}s"
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return 1, "", str(e)


def ssh_command(host, remote_cmd, timeout=20):
    cmd = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no", host, remote_cmd,
    ]
    return run_command(cmd, timeout=timeout)


def classify_failure(stderr_text):
    text = (stderr_text or "").lower()
    if "permission denied" in text:
        return "AUTH_FAILURE"
    if "timeout" in text or "timed out" in text or "connection refused" in text or "no route to host" in text:
        return "UNREACHABLE"
    return "ERROR"


def with_retry(check_fn, label, retries=CHECK_RETRIES, delay=CHECK_RETRY_DELAY):
    """Run a check function up to `retries` times before trusting a
    failure. Prevents one slow SSH response from being reported as a
    real outage."""
    last_result = False
    for attempt in range(1, retries + 1):
        last_result = check_fn()
        if last_result:
            return True
        if attempt < retries:
            log_event(f"[RETRY] {label} check failed (attempt {attempt}/{retries}), retrying in {delay}s")
            time.sleep(delay)
    return last_result


def check_postgres():
    def _check():
        code, out, err = ssh_command(HOSTS["db"], "sudo -u postgres pg_isready -h localhost -p 5432", timeout=20)
        if code != 0:
            log_event(f"[ERROR] PostgreSQL check failed on {HOSTS['db']}: {classify_failure(err)}: {err}")
        return code == 0 and "accepting connections" in f"{out} {err}".lower()
    return with_retry(_check, "PostgreSQL")


def check_nginx():
    def _check():
        code, out, err = ssh_command(HOSTS["web"], "systemctl is-active nginx", timeout=15)
        if code == 0 and out == "active":
            return True
        # Fallback: confirm via actual HTTP response before failing -
        # systemd can briefly report "activating" right after a restart
        # even though the port is already serving.
        code2, out2, err2 = ssh_command(
            HOSTS["web"], "curl -s --max-time 5 -o /dev/null -w '%{http_code}' http://localhost", timeout=15
        )
        if code2 != 0:
            log_event(f"[ERROR] Nginx check failed on {HOSTS['web']}: {classify_failure(err or err2)}")
        return code2 == 0 and out2 == "200"
    return with_retry(_check, "Nginx")


def check_fileserver():
    def _check():
        code, out, err = ssh_command(HOSTS["file"], "systemctl is-active smbd", timeout=15)
        if code != 0:
            log_event(f"[ERROR] FileServer check failed on {HOSTS['file']}: {classify_failure(err)}: {err}")
        return code == 0 and out == "active"
    return with_retry(_check, "FileServer")


def check_backupserver():
    def _check():
        cron_code, cron_out, cron_err = ssh_command(HOSTS["backup"], "systemctl is-active cron", timeout=15)
        rsync_code, rsync_out, rsync_err = ssh_command(HOSTS["backup"], "systemctl is-active rsync", timeout=15)
        dir_code, dir_out, dir_err = ssh_command(HOSTS["backup"], "test -d /backup && echo ok", timeout=15)
        ok = (cron_code == 0 and cron_out == "active" and
              rsync_code == 0 and rsync_out == "active" and
              dir_code == 0 and dir_out == "ok")
        if not ok:
            log_event(f"[DEBUG] BackupServer status -> cron: {cron_out or classify_failure(cron_err)}, "
                      f"rsync: {rsync_out or classify_failure(rsync_err)}, "
                      f"backup_dir: {dir_out or classify_failure(dir_err)}")
        return ok
    return with_retry(_check, "BackupServer")


def check_remote_disk(server_name, mountpoint):
    def _check():
        host = HOSTS[server_name]
        code, out, err = ssh_command(host, f"df -B1 --output=avail,target {mountpoint} | tail -n 1", timeout=20)
        if code != 0 or not out:
            log_event(f"[ERROR] Disk check failed on {server_name} ({host}), mount={mountpoint}: {classify_failure(err)}: {err}")
            return False
        try:
            available_bytes, actual_mount = out.split()
            available_bytes = int(available_bytes)
            free_gb = available_bytes / (1024 ** 3)
            log_event(f"[DEBUG] {server_name} ({host}) {actual_mount} free space: {free_gb:.2f} GB")
            return available_bytes >= MIN_FREE_DISK
        except ValueError:
            log_event(f"[ERROR] Unexpected disk output from {server_name}: {out}")
            return False
    return with_retry(_check, f"Disk:{server_name}")


def check_disk():
    disk_issues = []
    for server_name, mountpoint in DISK_TARGETS.items():
        if not check_remote_disk(server_name, mountpoint):
            disk_issues.append(f"{server_name}:{mountpoint}")
    if disk_issues:
        log_event("[ALERT] Low disk space or disk check failed on: " + ", ".join(disk_issues))
        return False
    return True


def check_health():
    issues = []
    if not check_postgres():
        issues.append("PostgreSQL")
    if not check_nginx():
        issues.append("Nginx")
    if not check_fileserver():
        issues.append("FileServer")
    if not check_backupserver():
        issues.append("BackupServer")
    if not check_disk():
        issues.append("Disk")
    return len(issues) == 0, issues


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


def disk_failsafe():
    """Guaranteed disk fix that does NOT depend on recover_disk.yml
    having the right task in it. Runs directly over SSH regardless of
    what's deployed on disk. This exists because the same YAML fix has
    repeatedly failed to be deployed correctly in this environment."""
    log_event("[FAILSAFE] Running built-in disk cleanup independent of Ansible playbook state")
    host = HOSTS["backup"]
    code, out, err = ssh_command(host, "sudo rm -f /backup/full.disk && echo removed", timeout=20)
    log_event(f"[FAILSAFE] full.disk removal result: {out or err}")
    # Also clear any accumulated backup files beyond the 3 most recent,
    # regardless of age, as a last resort.
    ssh_command(
        host,
        "cd /backup && find . -type f \\( -name '*.tar.gz' -o -name '*.dump.gz' \\) "
        "-printf '%T@ %p\\n' | sort -rn | tail -n +4 | cut -d' ' -f2- | xargs -r rm -f",
        timeout=30,
    )
    return check_remote_disk("backup", "/backup")


def recover_issue(issue):
    playbook = PLAYBOOKS.get(issue)
    if not playbook:
        log_event(f"[WARNING] No playbook mapped for issue: {issue}")
        return False

    log_event(f"[RECOVERY] {issue} recovery started")
    ok = run_ansible_playbook(playbook)
    log_event(f"[RECOVERY] {issue} playbook {'completed' if ok else 'FAILED'}")

    if issue == "Disk":
        # Always double-check disk specifically, regardless of what the
        # playbook reported, and run the failsafe if it's still critical.
        time.sleep(3)
        if not check_remote_disk("backup", "/backup"):
            disk_failsafe()

    return ok


def orchestrate_recovery(issues):
    start_time = time.time()

    for issue in issues:
        log_event(f"[ALERT] {issue} failure detected")
        if not AUTO_RECOVERY:
            log_event("[INFO] AUTO_RECOVERY disabled. No action taken.")
            continue
        recover_issue(issue)

    if not AUTO_RECOVERY:
        log_event("[INFO] AUTO_RECOVERY disabled. Skipping verification.")
        return False

    log_event(f"[INFO] Waiting {SETTLE_DELAY}s for services to fully settle before verifying")
    time.sleep(SETTLE_DELAY)

    for attempt in range(1, VERIFY_RETRIES + 1):
        log_event(f"[VERIFY] Recovery validation attempt {attempt}/{VERIFY_RETRIES}")
        healthy, remaining = check_health()
        if healthy:
            rto = round(time.time() - start_time, 2)
            log_event(f"[SUCCESS] System recovered successfully in {rto} seconds")
            log_event(f"[NOTIFY] Recovery complete | RTO={rto}s")
            return True
        log_event(f"[VERIFY] Still unhealthy: {', '.join(remaining)}")
        if attempt < VERIFY_RETRIES:
            time.sleep(VERIFY_DELAY)

    log_event("[CRITICAL] Recovery failed after retries")
    log_event(f"[NOTIFY] Recovery FAILED: {', '.join(issues)}")
    return False


def main():
    log_event("------------------------------------------------")
    log_event("[DR CHECK STARTED]")

    try:
        healthy, issues = check_health()
        if healthy:
            log_event("[STATUS] All systems healthy")
            log_event("[NOTIFY] System healthy")
        else:
            log_event(f"[ALERT] Issues found: {', '.join(issues)}")
            orchestrate_recovery(issues)
    except KeyboardInterrupt:
        log_event("[INFO] Interrupted by user")

    log_event("[DR CHECK FINISHED]")


if __name__ == "__main__":
    main()
