# Setup Guide - Build This System From Scratch

This is the single document to follow to implement the entire DR/BC system on fresh virtual machines, with no prior context needed beyond what's in this repository. Every command below was actually run and verified against the live infrastructure documented in `Final_Project_Report.docs`.

## 1. what you're building

Four virtual machines, each running one critical service, with a central backup/DR control node that monitors and automatically recovers the other three:

| Host | Role | Key Service | IP |
|---|---|---|---
| `webserver` | Web tier | Nginx | 192.168.52.3 |
| `dbserver` | Database tier | PostgreSQL 16 | 192.168.52.4 |
| `backupserver` | Backup / DR control | cron, Ansible, M/Monit, orchestrator | 192.168.52.5 |
| `fileserver` | File tier | Samba (smbd) | 192.168.5.6 |

## 1. Prerequisites

- A hypervisor (VirtualBox , Vmware, or promox all work) capable of running 4 Vms concurrently. **Undersizing this causes real problems**
- see the "Known limitation" note in the main README about host resource starvation causing kernel lockups under load.
- 4x Ubuntu Server 22.14+ installations, each with a static IP on a shared internal/host-only network so they can reach other.
- A non-root user on each VM matching `inventory.ini`'s `ansible_user` (e.g. the `webserver` user on the webserver VM, etc.) - this project uses a username matching the hostname for clarity, any username works as long as `inventory.ini` matches.

## 2. Install required software, per host

**On webserver:**
```bash
sudo apt update && sudo apt intall -y nginx monit
```

**On dbserver:**
```bash
sudo apt update && sudo apt install -y postgreql postgresql-contrib monit
sudo -u postgres createdb healthcare_db
```
**On fileserver:**
```bash
sudo apt update && sudo apt install -y samba monit
sudo mkdir -p /uploads && sudo chown fileserver:fileserver /uploads
```
Add a share definition to `/etc/samba/smb.conf`:
```ini
[uploads]
   path = /upload
   browseable = yes
   writable = yes
```
```bash
sudo systemctl restart smbd
```

**On backupserver:**
```bash
sudo apt update && sudo apt install -y ansible python3 python3-pip rsync monit git
sudo mkdir -p /backup/{database,files,webserver,logs,scripts}
sud chown -R backupserver:backupserver /backup
```

Install M/Monit 
```bash
sudo tar xzf mmonit-*.tar.gz -C /opt/
sudo mv /opt/mmonit-* /opt/mmonit-4.3.4   
```

## 3. SSH trus - both directions

**Direction 1: backupserver -> the other three hosts**
```bash
# on backupserver
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
ssh-copy-id webserver@192.168.52.3
ssh-copy-id dbserver@192.168.52.4
ssh-copy-id fileserver@192.168.52.6

for h in webserver@192.168.52.3 dbserver@192.168.52.4 fileserver@192.168.52.6; do
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$h" "echo $h Ok"
done
```
**Direction 2: each of the other three hosts -> backupserver**
```bash
# on webserver, dbserver, and fileserver individually:
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_dr_trigger
ssh-copy-id -i ~/.ssh/id_dr_trigger.pub backupserver@192.168.52.5
ssh -i ~/.ssh/id_dr_trigger backupserver@192.168.52.5 "echo ok"
```
## 4. Passwordless sudo - required or Ansible will hang

On **all four hosts**:
```bash
sudo visudo -f /etc/sudoers.d/ansible-nopasswd
```
Add one line (substitute that host's actual username)
```
webserver ALL=(ALL) NOPASSWD: ALL
```
Confirm:
```bash
sudo -l -U webserver
```

## 5. Deploy scripts to the right hosts
Everything under `scripts/` and `ansible/` runs **from backupserver** (it reaches out to the other hosts over SSH) - nothing needs to be copied to webserver, dbserver, or fileserver individually. Just confirm the directory structure landed correctly:
```bash
ls /backup/scripts/
ls /backup/scripts/ansible/
```

Set executable permissions if they weren't preserved by your transfer method:
```bash
chmod +x /backup/scripts/*,sh /backup/scripts/*.py
```

## 6. Verify the Ansible inventory matches your actual IPa

Open `ansible/inventory.ini` and confirm every IP matches your real VMs. Test connectivity:
```bash
cd /backup/scripts/ansible
ansible -i inventory.ini all -m ping
```

All four should return 'SUCCESS', If any don't, stop here and fix SSH trust (step 3) before continuing.

## 7. Test each recovery playbook individually before trusting the orchestrator

```bash
ansible-playbook -i inventory.ini setup_web.yml
ansible-playbook -i inventory.ini healthcare.yml
ansible-playbook -i inventory.ini recover_postgres.yml
ansible-playbook -i inventory.ini recover_nginx.yml
ansible-playbook -i inventory.ini recover_fileserver.yml
ansible-playbook -i inventory.ini recover_backupserver.yml
ansible-playbook -i inventory.ini recover_disk.yml
```

Each should report`ok`/`changed`, never `UNREACHABLE` or `failed`.

## 8. Wire up Monit and M/Monit

Install the persistent M/Monit service so it survives reboots and crashes instead of needing to be started manually:
```bash
sudo cp monit/mmonit.service /etc/systemd/system/mmonit.service
sudo systemctl daemon-reload
sudo systemctl enable --now mmonit
systemctl status mmonit
```
Follow `monit/MONIT_AUTOTRIGGER_GUIDE.md` to add the exec-based auto-recovery triggers to each host's Monit config (nginx on webserver, postgresql on dbserver, smbd on fileserver, disk threshold on backupserver). Monit has no `netbios` protocol , duplicate service name across config files silently break one of them, and Ubuntu already ships a default `rootfs` filesystem check that a custom one with the same name will conflct with.

After each config change:
```bash
sudo monit -t
sudo monit reload
```

## 9. Schedule backups and the orchestrator via cron

On backupserver, `crontab -e`:
```
0 */6 * * * /usr/bin/python3 /backup/scripts/backup_dbpostgre.py >> /backup/logs/backup_db.log 2>&1
0 2 * * * /bin/bash /backup/scripts/backup_fileserver.sh
30 2 * * * /bin/bash /backup/scripts/backup_webserver.sh
*/5 * * * * /usr/bin/python3 /backup/scripts/dr_orchestrator143.py >> /backup/logs/cron_dr.log 2>&1
```

## 10. Run the full verification sequence

```bash

# 1. Confirm baseline healthy
python3 /backup/scripts/dr_orchestrator143.py
tail -20 /backup/logs/dr_alerts.log

# 2. Test each failure type individually
python3 /backup/scripts/disaster_sim143.py postgresql
python3 /backup/scripts/dr_trigger.sh
tail -30 /backup/logs/dr_alerts.log

python3 /backup/scripts/disaster_sim143.py nginx
python3 /backup/scripts/dr_trigger.sh
tail -30 /backup/logs/dr_alerts.log

python3 /backup/scripts/disaster_sim143.py disk
python3 /backup/scripts/dr_trigger.sh
tail -30 /backup/logs/dr_alerts.log

# 3. Confirm the dashboard agrees
# open http://<backupserver-ip>:8080/status/hosts/ - all 4 should be green
```

Expected rsults, based on the measured runs documented in 'Final_Project_Reports.docx' Section 8: PostgreSQL and nginx recover in roughly 15 seconds, disk recovery, when it requires escalating to the built-in Python failsafe, takes roughly 35 seconds, file server recovery has been observed taking significantly longer (~100s) and is flagged in that report as an open item worth investigating further rather than a settled result.

## 11. What "done" look like
- `ansible -i inventory.ini -m ping` - all 4 succeed.
- M/Monit dashboard at 'http://<backupserver-ip>:8080' - all 4 hosts green.
- Each disaster type in step 10 recovers automatically with a logged RTO, with no manualrestart of any service required.
-`crontab -l` on backupserver shows the orchestrator running every 5 minutes without you needing to trigger it by hand.

If any of the above doesn't hold, 'docs/CHANGELOG.md' documents every defect found during this project's own development in the order it was found - most new problems on a fresh setup will resemble something alredy diagnosed there.
