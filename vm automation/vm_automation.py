import subprocess
import time

VBOX = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
VMS = ["backupserver", "Web Server 1", "dbserver", "fileserver"]

def run(args):
  subprocess.run([VBOX] + args, check=True)

def list_vms():
  run(["list", "vms"])

def start_all():
  for vm in VMS:
    run(["startvm", vm, "--type", "headless"])
    time.sleep(5)

def stop_all():
  for vm in reversed(VMS):
    run(["controlvm", vm, "acpipowerbutton"])
    time.sleep(5)

if __name__=="__main__":
    list_vms()
    start_all()
