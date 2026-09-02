# Making Monit auto-trigger recovery instantly

## Why this is needed
Now, recovery only happens two ways: running dr_orchestrator143.py
by hand, or cron running it every 5 minutes. Monit already *detects* failures in real time (Dashboard shows) but nothing currently makes it *act* on them except webserver's nginx check, and even that one had a broken exec line until recently. this wires all four hosts the same way.

## Add exec triggers to each host's monit config

**webserver** (`/etc/monit/conf.d/nginx.conf`) - already fixed, confirm it reads:
```
if failed port 80 protocol http then exec "/usr/bin/ssh -i /home/webserver/.ssh/is_dr_trigger backupserver@192.168.52.5 /backup/scripts/dr_trigger.sh"
```
**dbserver** (`/etc/monit/conf.d/postgresql`) - create if it doesn't exist:
```
check process postgresql with pidlife /var/run/postgresql/14-main.pid
    start program = "/usr/sbin/service postgresql start"
    stop program = "/usr/sbin/service postgresql stop"
    if failed port 5432 protocol pgsql then alert
    if failed port 5432 protocol pgsql then exec "/usr/bin/ssh -i /home/dbserver/.ssh/id_dr_trigger backupserver@192.168.52.5 /backup/scripts/dr_trigger.sh"
```
(Adjust the pidlife path to match your actual PostgreSQL version's path- check with 'sudo find / -name "*.pid" -path " *postgresql*"' is unsure.)

**fileserver** (`/etc/monit/conf.d/smbd`):
```
check process smbd with pidlife /run/samba/smbd.pid
    start program = "/usr/sbin/service smbd start"
    stop program = "/usr/sbin/service smbd stop"
    if failed port 445 protcol netbios then alert
    if failed port 445 protcol netbios then exec "/usr/bin/ssh -i /home/fileserver/.ssh/id_dr_trigger backupserver@192.168.52.5 /backup/scripts/dr_trigger.sh"
```
**backupserver** (`/etc/monit/conf.d/disk`) - this one runs locally, no SSH needed:

```
check filesystem rootfs with path /backup
    if space usage > 90% then exec "/bin/bash /backup/scripts/dr_trigger.sh"
```

## Apply and verify on each host
```bash
sudo monit -t
sudo monit reload
``` 

## Test end-to-end without waiting for a real failure
```bash
# on backupserver, confirm dr_trigger.sh runs cleanly on its own first
bash /backup/scipts/dr_trigger.sh
tail -20 /backup/logs/dr_alerts.log

# then trigger a real failure and confirm monit fires it automatically
python3 /backup/scripts/disaster_sim143.py
# watch the log WITHOUT running anything else manually:
tail -f /backup/logs/dr_alerts.log
```

If wired correctly, you should see a `[DR CHECK STARTED]` entry appear within seconds of the simulated failure, not after up to 5 minutes.

## Keep cron as a safety net, not the only trigger
- Monit's exec actions catch failures within seconds.
- Cron's `*/5 * * * *` catches anything Monit's specific checks don't cover (e.g. if Monit's own agent crashes, cron still runs independently).

