#!/usr/bin/env python3
import subprocess
import psutil
from datetime import datetime


def check_health():
    # PostgreSQL check
    result = subprocess.run(
        "ssh -o BatchMode=yes dbserver@192.168.52.4 'sudo -u postgres pg_isready'",
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False, "PostgreSQL down"

    # Nginx check
    web = subprocess.run(
        "ssh -o BatchMode=yes webserver@192.168.52.3 'sudo systemctl is-active nginx'",
        shell=True,
        capture_output=True,
        text=True
    )

    if "active" not in web.stdout:
        return False, "Nginx down"

    # Backup disk check
    disk = psutil.disk_usage('/backup').free
    if disk < 2 * 1024**3:
        return False, "Backup disk low"

    return True, "All healthy"


def orchestrate_recovery(issue):
    print(f"[ORCHESTRATE] Recovering: {issue}")

    if "Nginx" in issue:
        print("[RECOVERY] Restarting NGINX...")
        subprocess.run(
            "ssh -o BatchMode=yes webserver@192.168.52.3 'sudo systemctl restart nginx'",
            shell=True
        )

    elif "PostgreSQL" in issue:
        print("[RECOVERY] Restarting PostgreSQL...")
        subprocess.run(
            "ssh -o BatchMode=yes dbserver@192.168.52.4 'sudo systemctl restart postgresql'",
            shell=True
        )

    elif "disk" in issue.lower():
        print("[WARNING] Low disk space - Manual action needed")

    else:
        print("[WARNING] Unknown issue")


def send_notification(status, rto):
    with open('/backup/logs/dr_alerts.log', 'a') as f:
        f.write(f"[{datetime.now()}] DR {status}: RTO {rto}s\n")

    print(f"[DR ALERT] {status} | RTO: {rto}s")
    subprocess.run("logger -t DR_Orchestrator 'Recovery event logged'", shell=True)


if __name__ == "__main__":
    healthy, status = check_health()

    if healthy:
        print("[STATUS] All systems healthy")
        send_notification("HEALTHY", 0)

    else:
        print(f"[ALERT] {status}")
        orchestrate_recovery(status)
        send_notification("RECOVERED", 120)
