# 🏥 Disaster Recovery & Business Continuity System
## A Self-Healing Healthcare Infrastructure Platform

### 🎯 What This Does (In Plain English)

Imagine your hospital's systems go down. **This system automatically detects what broke and fixes it** — without waiting for a human to notice or manually intervene.

```
Normal Day:
  ✅ PostgreSQL (Database) → Running
  ✅ Nginx (Website) → Running  
  ✅ Samba (File Server) → Running
  ✅ Backups → Running

Disaster Happens:
  ❌ PostgreSQL crashes

What Happens Next (Automatically):
  🔍 [14:32:10] Orchestrator detects PostgreSQL is down
  📧 [14:32:11] Sends email alert to ops team
  🔧 [14:32:12] Runs recovery playbook (restarts PostgreSQL)
  ⏱️  [14:32:15] Waits for database to fully boot
  ✅ [14:32:28] Verifies database is accepting connections
  📊 [14:32:29] Logs: "PostgreSQL recovered in 18 seconds"
  ✔️ [14:32:30] Back to normal — team got paged, didn't have to notice

Result: ~18 seconds downtime instead of "unknown + hours of manual work"
```

---

## 🏗️ The Architecture (What Runs Where)

```
┌─────────────────────────────────────────────────────────────────┐
│                      YOUR HOSPITAL NETWORK                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  🌐 WEBSERVER (192.168.52.3)          📦 FILESERVER (192.168.52.6) │
│  ├─ Nginx (web app)                   ├─ Samba (file shares)       │
│  ├─ Monit agent                       ├─ Monit agent               │
│  └─ Sends heartbeat to backup server  └─ Sends heartbeat           │
│                                                                   │
│  🗄️ DBSERVER (192.168.52.4)                                       │
│  ├─ PostgreSQL (healthcare data)                                 │
│  ├─ Monit agent                                                  │
│  └─ Sends heartbeat to backup server                             │
│                                                                   │
│  💾 BACKUPSERVER (192.168.52.5) ← COMMAND CENTER                 │
│  ├─ M/Monit Dashboard (sees all alerts)                          │
│  ├─ DR Orchestrator (brain of the system)                        │
│  │   ├─ Every 5 minutes: checks if everything is healthy         │
│  │   ├─ If problem found: runs recovery playbooks                │
│  │   ├─ Measures recovery time (RTO)                             │
│  │   └─ Sends alerts via email                                   │
│  ├─ Ansible (executes recovery commands)                         │
│  └─ Backup Storage (nightly database/file backups)               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Flow: All services have local Monit agents
      → Send status to central M/Monit dashboard
      → Orchestrator queries dashboard every 5 min
      → If something is down, trigger recovery via Ansible
      → Monitor verifies it's back up
      → Send email to ops team
```

---

## 📂 Repository Structure (Easy Navigation)

```
Disaster-Recovery-and-Buisness-Continuity/
│
├── 📄 README.md (this file) ............. Project overview + quick start
├── AGENTS.md ........................... AI/Copilot reference guide
│
├── 🎮 ansible/ ......................... Recovery & Setup Playbooks
│   ├── healthcare.yml ................. Deploy monitoring (Netdata)
│   ├── recover_postgres.yml ........... Fix database when it crashes
│   ├── recover_nginx.yml .............. Fix web server when it crashes
│   ├── recover_fileserver.yml ......... Fix file server when it crashes
│   ├── recover_backupserver.yml ....... Fix backup services when down
│   ├── recover_disk.yml ............... Clear disk space (cleanup old backups)
│   ├── recover_disk_emergency.yml ..... NUCLEAR OPTION: delete everything old
│   ├── setup_web.yml .................. Initial setup (Nginx + monitoring)
│   └── inventory.ini .................. List of all 4 servers + their IPs
│
├── 🐍 scripts/ ......................... Orchestration & Automation (30+ files)
│   │
│   ���── 🧠 THE ORCHESTRATORS (The Brain)
│   │   ├── dr_orchestrator143.py ...... ⭐ USE THIS ONE (main logic, v1.4.3)
│   │   ├── dr_trigger.sh .............. Manually trigger orchestrator
│   │   └── dr_orchestrator*.py ........ Old versions (use only if told to)
│   │
│   ├── 💥 FAILURE TESTING (Inject Problems to Test Recovery)
│   │   └── disaster_sim143.py ......... Create fake database/disk/nginx crashes
│   │
│   ├── 💾 BACKUPS (Run Nightly, Automatically)
│   │   ├── backup_postgresql.sh ....... Database dumps (pg_dump)
│   │   ├── backup_dbpostgre.py ........ Alternative DB backup method
│   │   ├── backup_fileserver.sh ....... File share backups (rsync)
│   │   └── backup_webserver.sh ........ Website config backups (tar)
│   │
│   ├── 🔄 RESTORE (Manual Point-in-Time Recovery)
│   │   ├── restore_dbpostgre.py ....... Restore database from backup
│   │   ├── restore_fileserver.py ...... Restore files from backup
│   │   └── restore_monitor.py ......... Restore monitoring config
│   │
│   ├── 📊 DASHBOARDS & MONITORING
│   │   ├── dashboard_simple.py ........ Show system status in terminal
│   │   ├── monitor_healthcare.py ...... Health check script
│   │   └── authorized_keys ........... SSH keys for passwordless access
│   │
│   └── 📋 Logs (auto-created, track what happened)
│       ├── backup.log ................. Last backup run output
│       ├── restore.log ................ Last restore run output
│       ├── dashboard.log .............. Dashboard run logs
│       └── nohup.out .................. Background process logs
│
├── 🔍 monit/ .......................... Monitoring Agent Setup
│   ├── MONIT_AUTOTRIGGER_GUIDE.md .... How to connect M/Monit to recovery
│   └── mmonit.service ................ Run M/Monit as a service
│
├── 📚 docs/ ........................... Step-by-Step Guides
│   ├── SETUP_GUIDE.md ................ Build this from 4 bare Ubuntu VMs
│   ├── IMPLEMENTATION_GUIDE.md ....... Deploy & schedule on production
│   ├── UPGRADE_GUIDE_PHASE1.md ....... Add JSON logging + email alerts
│   ├── Final_Project_Report.pdf ...... Live test results: RTO/RPO metrics
│   ├── DRBC-Project-Report.docx ...... Detailed technical report
│   └── DIASASTER_RECOVERY_&_BUSINESS_CONTINUITY.pptx ... Presentation
│
├── 📈 results/ ........................ Test Results & Performance Data
│   └── (RTO measurements, incident logs, metrics)
│
└── 🖥️ vm_automation/ .................. VM Provisioning (Optional)
    └── Auto-create VMs in VirtualBox/Proxmox

```

---

## 🚀 Quick Start (5 Minutes)

### Option 1: Just Want to See It Work?

```bash
# 1. Clone this repo to your backupserver
git clone https://github.com/athultpme/Disaster-Recovery-and-Buisness-Continuity.git
cd Disaster-Recovery-and-Buisness-Continuity

# 2. Check if all 4 servers are reachable
ansible -i ansible/inventory.ini all -m ping

# 3. Run orchestrator once (checks everything)
python3 scripts/dr_orchestrator143.py

# 4. Inject a fake failure to test auto-recovery
python3 scripts/disaster_sim143.py postgresql

# 5. Watch it recover automatically
tail -f /backup/logs/dr_alerts.log

# 6. View system status
python3 scripts/dashboard_simple.py
```

### Option 2: Full Setup From Scratch

**[🔗 See docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** — Complete step-by-step guide (11 sections, ~30 min)

Includes:
- How to create 4 Ubuntu VMs
- What software to install on each
- SSH trust setup (passwordless)
- Ansible inventory configuration
- Cron scheduling for automation
- Full verification walkthrough

### Option 3: Understand the Code

**[🔗 See docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** — How each piece works & fits together

---

## 🎓 How It Works (The Magic Inside)

### The 5-Minute Health Check Cycle

```python
# Every 5 minutes, this runs automatically (cron job):

1. CHECK HEALTH ─────────────────────────────────────
   ├─ Is PostgreSQL responding? (pg_isready)
   ├─ Is Nginx serving HTTP 200? (systemctl + curl)
   ├─ Is Samba file server active? (systemctl smbd)
   ├─ Is backup server running? (cron + rsync checks)
   └─ Is disk space > 1 GB on all hosts? (df check)

2. IF ANYTHING IS DOWN ──────────────────────────────
   ├─ Log: "[ALERT] PostgreSQL failure detected"
   ├─ Send email to ops team (optional)
   └─ Trigger recovery

3. RECOVERY PHASE ──────────────────────────────────
   ├─ Run Ansible playbook (e.g., recover_postgres.yml)
   │  └─ This does: systemctl restart postgresql
   ├─ Wait 10 seconds for service to fully boot
   └─ Verify 3 times (with retries for transient issues)

4. MEASURE SUCCESS ────────────────────────────────
   ├─ If healthy: log "[SUCCESS] recovered in 14.2s"
   ├─ If still down: log "[CRITICAL] Recovery FAILED"
   └─ Calculate RTO (Recovery Time Objective)

5. NOTIFY TEAM ────────────────────────────────────
   ├─ Email with component, severity, RTO
   └─ Log to /backup/logs/dr_alerts.log
```

**Real example from live testing:**

```
[2025-09-12 14:32:10] [ALERT] PostgreSQL failure detected
[2025-09-12 14:32:11] [INFO] Running playbook: recover_postgres.yml
[2025-09-12 14:32:12] TASK [Restart PostgreSQL service]
[2025-09-12 14:32:13] changed: [dbserver -> 192.168.52.4]
[2025-09-12 14:32:15] [INFO] Waiting 10s for services to fully settle
[2025-09-12 14:32:25] [VERIFY] Recovery validation attempt 1/3
[2025-09-12 14:32:28] [SUCCESS] System recovered successfully in 18.2 seconds
[2025-09-12 14:32:29] ✅ PostgreSQL is now healthy
```

---

## 🧪 Test It (Chaos Engineering)

The best way to prove your system works is to **break it intentionally** and verify it fixes itself:

### Inject a Fake Failure

```bash
# Simulate database crash
python3 scripts/disaster_sim143.py postgresql

# Simulate web server crash
python3 scripts/disaster_sim143.py nginx

# Simulate disk full
python3 scripts/disaster_sim143.py disk

# See all available failure types
python3 scripts/disaster_sim143.py --list

# Trigger recovery manually (after injecting failure)
bash scripts/dr_trigger.sh

# Watch the magic happen
tail -30 /backup/logs/dr_alerts.log
```

### Expected Results (From Live Testing)

| Failure Type | Detection Time | Recovery Time | Success Rate |
|---|:---:|:---:|:---:|
| 🗄️ PostgreSQL Down | <5 sec | 12-18 sec | 100% |
| 🌐 Nginx Down | <5 sec | 8-12 sec | 100% |
| 📁 Samba Down | <5 sec | 10-15 sec | 100% |
| 💿 Disk Full | <10 sec | 20-40 sec | 95% |
| **🎯 Average RTO** | - | **15.2 sec** | **98.75%** |

*(Full test data available in [Final_Project_Report.pdf](docs/Final_Project_Report.pdf))*

---

## 📊 What Failures Can It Detect & Fix?

The system handles 6 critical failure scenarios automatically:

| Component | Detection Method | Recovery Action | Result |
|---|---|---|---|
| **🗄️ PostgreSQL** | `pg_isready` over SSH | Restart database service | Reconnects in 12-18s |
| **🌐 Nginx** | `systemctl` + HTTP 200 check | Restart web service | Serving in 8-12s |
| **📁 Samba** | `systemctl is-active smbd` | Restart file service | Shares available in 10-15s |
| **💾 Backup Server** | Check cron/rsync/backup dir | Restart backup services | Backups resume in 15-25s |
| **💿 Low Disk** | `df` on all 4 hosts | Delete backups >14 days old | Frees space in 20-40s |
| **💿 Critical Disk** | Disk still full after cleanup | Delete everything except 3 newest | Emergency cleanup in 30-60s |

Each recovery includes **automatic verification** (retries 3 times to avoid false positives).

---

## 🔐 Security Features

| Feature | Implementation | Why It Matters |
|---|---|---|
| ✅ **Passwordless SSH** | SSH key-based auth (no passwords) | No credentials in scripts |
| ✅ **Sudoers NOPASSWD** | Pre-configured for Ansible | No password prompts = true automation |
| ✅ **Encrypted Backups** | Optional (configure in your backup scripts) | Protect healthcare data in transit |
| ✅ **Firewall Rules** | Netdata only from admin subnet | Monitoring dashboard not internet-facing |
| ✅ **Email Credentials** | Stored in environment variables | Not hardcoded in scripts |
| ✅ **Monit Credentials** | Should be changed from defaults | See MONIT_AUTOTRIGGER_GUIDE.md |

---

## 📖 Documentation Map (Choose Your Path)

| I Want To... | Read This |
|---|---|
| **Understand what this project does** | This README (you're reading it!) |
| **Build this from scratch** | [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) |
| **Deploy to production** | [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) |
| **See live test results** | [docs/Final_Project_Report.pdf](docs/Final_Project_Report.pdf) |
| **Wire up Monit alerts** | [monit/MONIT_AUTOTRIGGER_GUIDE.md](monit/MONIT_AUTOTRIGGER_GUIDE.md) |
| **Add JSON logging + email alerts** | [docs/UPGRADE_GUIDE_PHASE1.md](docs/UPGRADE_GUIDE_PHASE1.md) |
| **Give this as a presentation** | [docs/DIASASTER_RECOVERY_&_BUSINESS_CONTINUITY.pptx](docs/DIASASTER_RECOVERY_&_BUSINESS_CONTINUITY.pptx) |

---

## 🛠️ Common Commands

### Verify Everything Is Working

```bash
# Test Ansible can reach all 4 servers
ansible -i ansible/inventory.ini all -m ping

# Check all playbooks have valid syntax
ansible-playbook -i ansible/inventory.ini setup_web.yml --syntax-check
ansible-playbook -i ansible/inventory.ini recover_postgres.yml --syntax-check
ansible-playbook -i ansible/inventory.ini recover_nginx.yml --syntax-check
ansible-playbook -i ansible/inventory.ini recover_fileserver.yml --syntax-check
ansible-playbook -i ansible/inventory.ini recover_backupserver.yml --syntax-check
ansible-playbook -i ansible/inventory.ini recover_disk.yml --syntax-check

# Validate Python & shell scripts without running them
python3 -m py_compile scripts/dr_orchestrator143.py
python3 -m py_compile scripts/disaster_sim143.py
bash -n scripts/backup_*.sh
bash -n scripts/dr_trigger.sh
```

### Run the Orchestrator

```bash
# Run once manually (for testing/debugging)
python3 /backup/scripts/dr_orchestrator143.py

# Or use the wrapper script
bash /backup/scripts/dr_trigger.sh

# Watch the logs in real-time
tail -f /backup/logs/dr_alerts.log

# See the last 50 events
tail -50 /backup/logs/dr_alerts.log
```

### Schedule Automatic Checks (Add to Crontab)

```bash
# Edit crontab
crontab -e

# Add these lines:

# Backups (run nightly)
0 */6 * * * /usr/bin/python3 /backup/scripts/backup_dbpostgre.py >> /backup/logs/backup_db.log 2>&1
0 2 * * * /bin/bash /backup/scripts/backup_fileserver.sh >> /backup/logs/backup_file.log 2>&1
30 2 * * * /bin/bash /backup/scripts/backup_webserver.sh >> /backup/logs/backup_web.log 2>&1

# Health checks (every 5 minutes)
*/5 * * * * /usr/bin/python3 /backup/scripts/dr_orchestrator143.py >> /backup/logs/cron_dr.log 2>&1
```

---

## ⚙️ Configuration

### Update Server IPs (Most Important!)

Edit `ansible/inventory.ini`:
```ini
[webserver]
webserver ansible_host=192.168.52.3 ansible_user=webserver

[dbserver]
dbserver ansible_host=192.168.52.4 ansible_user=dbserver

[fileserver]
fileserver ansible_host=192.168.52.6 ansible_user=fileserver

[backupserver]
backupserver ansible_host=192.168.52.5 ansible_user=backupserver

# ☝️ Replace these IPs with your actual server addresses
```

### Enable Email Alerts (Optional, But Recommended)

```bash
# Set environment variables (one-time or in ~/.bashrc)
export DR_ALERT_EMAIL="ops-team@hospital.com"
export SMTP_SERVER="mail.hospital.com"
export SMTP_PORT="587"
export SMTP_USER="dr-alerts@hospital.com"
export SMTP_PASS="your_app_password"

# Now run orchestrator (it will send alerts)
python3 scripts/dr_orchestrator143.py
```

### Change Disk Threshold

Edit `scripts/dr_orchestrator143.py` line 38:
```python
MIN_FREE_DISK = 1 * 1024**3  # Currently 1 GB

# Change to your needs:
MIN_FREE_DISK = 5 * 1024**3  # 5 GB if you want more buffer
```

---

## ❓ Frequently Asked Questions

**Q: How often does it check health?**  
A: Every 5 minutes (default). Configure in crontab — could be 1 min, 10 min, hourly, etc.

**Q: Why doesn't it check every minute?**  
A: To avoid alert fatigue. 5 minutes is industry standard for infrastructure checks.

**Q: What if something fails during recovery?**  
A: System logs `[CRITICAL]`, sends email alert, stops trying. Check logs and fix manually.

**Q: How do I test without breaking real services?**  
A: Use `disaster_sim143.py` — it injects fake failures that the orchestrator detects. Perfect for testing!

**Q: What if I get a false positive (transient network issue)?**  
A: Built-in retry logic checks 3 times with 3-second delays. One glitch won't trigger recovery.

**Q: Can this run multiple failures at once?**  
A: Yes! `check_health()` finds ALL problems first, then recovers each one systematically.

**Q: Is this specific to hospitals?**  
A: No — works for any infrastructure with PostgreSQL + web + file servers (universities, startups, etc).

**Q: How much disk space do I need for backups?**  
A: See SETUP_GUIDE.md Section 2 — typically 50-100 GB for 2 weeks of daily backups.

**Q: Can I modify the recovery playbooks?**  
A: Yes! They're in `ansible/` — just YAML files. Test with `ansible-playbook --syntax-check` first.

---

## 🏆 What Makes This Project Professional

| Aspect | Amateur Approach | This Project |
|---|---|---|
| **Failure Detection** | Manual: ops team watches monitors | Automated SSH health checks every 5 min |
| **Recovery** | Manual: ops SSH in, restart manually | Automatic Ansible playbooks, no human needed |
| **Verification** | "I think it's working" | Automated re-check 3x to confirm recovery |
| **Metrics** | "It recovered eventually" | Exact RTO measured in seconds |
| **Testing** | "Hope it works when needed" | Chaos engineering with disaster_sim143.py |
| **Documentation** | Vague runbooks | Step-by-step guides + code comments |
| **Compliance** | No audit trail | JSON logs provide HIPAA-compliant records |

---

## 🚀 What You Can Tell Your Professor

### The Original System (What You Built)

✅ **Multi-host architecture** — Monitors 4 independent servers from central point  
✅ **SSH-based diagnostics** — Detects failures without installing agents everywhere  
✅ **Automatic recovery** — Ansible playbooks trigger on specific conditions  
✅ **Retry logic** — Retries checks to avoid false positives from network blips  
✅ **RTO measurement** — Quantifies how fast recovery happens (in seconds)  
✅ **Production-tested** — Live tests on real VMs with complete metrics  
✅ **Built-in failsafe** — Python failsafe for disk recovery (doesn't rely solely on YAML)  

### Optional Upgrades (You Can Add These)

**Phase 1: JSON Logging + Email Alerts**
- Structured logging for dashboards & metrics
- SMTP-based notifications for critical failures

**Phase 2: Web Dashboard + Code Organization**
- Real-time health dashboard (Flask)
- Organized scripts/ directory structure

**Phase 3: Tests + CI/CD Pipeline**
- Unit tests with mocked SSH
- GitHub Actions for automated testing

**Phase 4: SLA Metrics & Compliance**
- Extract RTO/MTTF from logs
- HIPAA-compliant audit trail & reports

---

## 📞 Get Help

| Issue | Solution |
|---|---|
| **Setup problems?** | Read [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) Section 10 (Troubleshooting) |
| **Need to understand the code?** | Read [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) |
| **Monit won't send alerts?** | Read [monit/MONIT_AUTOTRIGGER_GUIDE.md](monit/MONIT_AUTOTRIGGER_GUIDE.md) |
| **Want to see what actually happened?** | Read [docs/Final_Project_Report.pdf](docs/Final_Project_Report.pdf) (live test results) |
| **Explaining this to your professor?** | Print the README + Final_Project_Report.pdf |

---

## 📜 License

MIT License — Use freely for learning, research, or production systems.

---

## 👥 Team

| Name | Role |
|---|---|
| Athul Thuvattu Paramabth | Team Lead / Project Manager |
| Thattarakkal Vishnu Viswanath | Virtual Infrastructure Engineer |
| Varghese Kuruvilla | Backup and Recovery Specialist |
| Anantha Krishnan Anil Kumar | Monitoring and Automation Developer |

**Course:** Infrastructure Systems (Prof. Igor Tomičić)  
**Date:** September 2025  
**Status:** ✅ Production-ready, tested, documented

---

**Questions? Start here:**
1. Read this README (5 min)
2. Follow [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) (30 min)
3. Run `python3 scripts/dr_orchestrator143.py` (1 min)
4. Test with `python3 scripts/disaster_sim143.py postgresql` (2 min)
5. Watch it recover automatically! ✨
