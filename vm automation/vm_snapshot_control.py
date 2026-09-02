import subprocess
import time
import os

VBOX = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
VMS = ["backupserver", "Web Server 1", "dbserver", "fileserver"]
SNAPSHOT_NAME = "Before_DR_Test"

def run(args):
    if not os.path.exists(VBOX):
        raise FileNotFoundError(f"VBoxManage not found at: {VBOX}")
    result = subprocess.run([VBOX] + args, check=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result

def list_vms():
    run(["list", "vms"])

def list_running_vms():
    run(["list", "runningvms"])

def start_all():
    for vm in VMS:
        print(f"Starting {vm}...")
        run(["startvm", vm, "--type", "headless"])
        time.sleep(5)

def stop_all():
    for vm in reversed(VMS):
        print(f"Stopping {vm}...")
        run(["controlvm", vm, "acpipowerbutton"])
        time.sleep(10)

def poweroff_vm(vm):
    print(f"Force stopping {vm}...")
    run(["controlvm", vm, "poweroff"])

def take_snapshot(vm, snapshot_name=SNAPSHOT_NAME):
    print(f"Taking snapshot of {vm}...")
    run(["snapshot", vm, "take", snapshot_name])

def list_snapshots(vm):
    print(f"Listing snapshots for {vm}...")
    run(["snapshot", vm, "list"])

def restore_snapshot(vm, snapshot_name=SNAPSHOT_NAME):
    print(f"Restoring snapshot for {vm}...")
    run(["snapshot", vm, "restore", snapshot_name])

if __name__ == "__main__":
    list_vms()
    list_running_vms()