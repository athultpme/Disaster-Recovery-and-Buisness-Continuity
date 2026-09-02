# DR/BC Project - Implementation Guide


## 1. Directory layout on backupserver

```
/backup/
|-- database/      # postgres_backup_*.dump.gz + postgres_backup_latest.gz symlink
|-- files/         # rsync backup + "latest" symlink
|-- webserver/     # nginx_config_*.tar.gz
|-- logs/          # all *.log files from every script below
|-- scripts/ 
    |-- backup_dbpostgre.py
    |-- backup_fileserver.sh
    |-- backup_webserver.sh
    |-- restore_dbpostgre.py
    |-- restore_fileserver.py
    |-- monitor_healthcare.py
    |-- dr_trigger.sh
    |-- dr_orchestrator.py
    |-- ansible/
        |-- inventory.ini
        |-- setup_web.yml
        |-- healthcare.yml
        |-- recover_postgres.yml
        |-- recover_nginx.yml
        |-- recover_fileserver.yml
        |-- recover_backupserver.yml
        |-- recover_disk.yml
        |-- recover_disk-emergency.yml
```

## 2. Fix SSH trus first - nothing else works until this passes

From backupserver, confirm passwordless SSH to all three other hosts

```bash
for h in webserver@192.168.52.3 dbsever@192.168.52.4 fileserver@192.168.52.6; do
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$h" "echo $h OK"
done
```
All three must print 'OK' with no prompt before continuing.

## 3. Deploy the Ansible layer

```bash
scp inventory.ini backupserver:/backup/scripts/ansible/
scp setup_web.yml healthcare.yml recover_*.yml backupserver:/backup/scripts/ansible/
```

Test each playbook individulally before trusting the orchestrator to call them:
```bash
cd /backup/scripts/ansible
ansible-playbook -i inventory.ini setup_web.yml    
ansible-playbook -i inventory.ini helathcare.yml  # deploys Netdata to all 4 hosts
ansible-playbook -i inventory.ini recover_postgres.yml
ansible-playbook -i inventory.ini recovery_nginx.yml
ansible-playbook -i inventory.ini recover_fileserver.yml
ansible-playbook -i inventory.ini recover_backupserver.yml
ansible-playbook -i inventory.ini recover_disk.yml
```
Each should report `ok`/`changed`, not ``UNREACHABLE` or `0 hosts matched`.

## 4. Deploy backup scripts + cron them

```bash
scp backup_dbpostgre.py backup_fileserver.sh restore_fileserver.py restore_dbpostgre.py backupserver:/backup/scripts/
chmod +x /backup/scripts/*.sh /backup/scripts/*.py
```

On backupserver, `crontab -e`
```

# DB backup every 6 hours
0 */6 * * * /usr/bin/python3 /backup/scripts/backup_dbpostgre.py >> / backup/logs/backup_db.log 2>&1
# File server backup nightly
0 2 * * * /bin/bash /backup/scripts/backup_fileserver.sh
# web server config backup nightly
30 2 * * * /bin/bash /backup/scripts/backup_webserver,sh
# Healthcare backup moitor, every 5 minutes
*/5 * * * * /usr/bin/python3 /backup/scripts/monitor_healthcare.py >> /backup/logs/monitor.log 2>&1
```
## 5. Deploy and schedule the DR orchestrator - this is the self-healing loop

```bash
scp dr_orchestrator.py dr_trigger.sh backupserver:/backup/scripts/
chmod +x /backup/scripts/dr_trigger.sh
```

`crontab -e`:
```
*/10 * * * * /bin/bash /backup/scripts/dr_trigger.sh >> /backup/logs/cron_dr.log 2>&1
```

This is what recovery automatic: every 10 minutes it checks health,
runs the matching playbook on failure, verifies up to 3 times, and - new in this version - escaltes to 'recover_disk_emergency.yml' if disk is still critical after those retries, instaed of just giving up.

## 6. End-toend test sequence

```bash
# 1. Confirm baseline healthy
python3 /backup/scripts/dr_orchestrator.py
tail -20 /backup/logs/dr_alerts.log        # expect "All systems healthy"

# 2. Inject a disaster
python3 /backup/scripts/disaster_sim143.py # picks one at random

# 3. Trigger recovery manually (don't wait for cron, for this test)
bash /backup/scripts/dr_trigger.sh
tail -60 /backup/logs/dr_alerts.log        # watch the recovery + verify cycle

# 4. Confirm recovery
ssh dbserver@192.168.52.4 "systemctl is-active postgresql"
ssh webserver@192.168.52.3 "systemctl is-active nginx"
df -h /backup
```
## 7. Monitoring layer

- Netdata (`healthcare.yml`) now reaches all 4 hosts and is restricted to
  the `192.168.52.0/24` subnet instaed of the open internet.
- Change Monit's default password (`monitrc` -> `set httpd ... allow admin:<new-password>`) - this was flagged live on your dashboard.
- `monitor_healthcare.py` now finds the real latest backup via glob instead of a hardcoded filename that never existed.