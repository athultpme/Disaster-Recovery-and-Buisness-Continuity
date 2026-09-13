# 🏗️ System Architecture & Design

**A Deep Dive into the DR/BC Infrastructure**

---

## 📑 Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [Component Layers](#component-layers)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Failure Detection Strategy](#failure-detection-strategy)
5. [Recovery Mechanisms](#recovery-mechanisms)
6. [Security Architecture](#security-architecture)
7. [Scalability & Limits](#scalability--limits)

---

## High-Level Overview

### System Principles

This system implements **self-healing infrastructure** based on three core principles:

```
1️⃣  DETECTION     → Continuous health monitoring
2️⃣  DIAGNOSIS     → Automated failure identification
3️⃣  REMEDIATION   → Automatic service recovery
```

### The Four-Tier Model

```
┌────────────────────────────────────────────────────────────┐
│  TIER 4: ORCHESTRATION LAYER                               │
│  (Backupserver: Central Brain)                             │
│  ├─ DR Orchestrator (Python)                               │
│  ├─ Ansible Engine                                          │
│  └─ M/Monit Dashboard                                       │
├────────────────────────────────────────────────────────────┤
│  TIER 3: MONITORING LAYER                                  │
│  (All Hosts: Local Monit Agents)                           │
│  ├─ Process Monitoring (service status)                     │
│  ├─ System Monitoring (disk, memory, CPU)                   │
│  └─ Application Monitoring (HTTP checks)                    │
├────────────────────────────────────────────────────────────┤
│  TIER 2: SERVICE LAYER                                     │
│  (Specialized Services)                                     │
│  ├─ Nginx (Webserver)      | PostgreSQL (DBserver)         │
│  ├─ Samba (Fileserver)     | Backup Services (Backupserver)│
│  └─ Cron (Scheduled Tasks) | SSH Daemon (All)              │
├────────────────────────────────────────────────────────────┤
│  TIER 1: INFRASTRUCTURE                                    │
│  (Virtual Machines & Network)                              │
│  ├─ Host-only Network (192.168.52.0/24)                    │
│  ├─ Storage (VM disks + backup storage)                    │
│  └─ Hypervisor (VirtualBox, Proxmox, etc.)                 │
└────────────────────────────────────────────────────────────┘
```

---

## Component Layers

### Layer 1: The Four Nodes

#### Webserver (192.168.52.3)
| Aspect | Details |
|---|---|
| **Role** | Frontend/HTTP tier |
| **Primary Service** | Nginx (web server) |
| **Secondary Services** | Monit agent, SSH daemon |
| **Data Stored** | Web configurations (backed up) |
| **Monitoring** | HTTP 200 checks, process status |
| **Recovery** | Service restart via systemctl |

#### DBServer (192.168.52.4)
| Aspect | Details |
|---|---|
| **Role** | Data persistence tier |
| **Primary Service** | PostgreSQL 16 |
| **Secondary Services** | Monit agent, SSH daemon |
| **Data Stored** | Healthcare database (critical) |
| **Monitoring** | `pg_isready`, connection tests |
| **Recovery** | Database restart + integrity check |

#### Fileserver (192.168.52.6)
| Aspect | Details |
|---|---|
| **Role** | File storage & sharing tier |
| **Primary Service** | Samba (SMB/CIFS) |
| **Secondary Services** | Monit agent, SSH daemon |
| **Data Stored** | Shared files (backed up) |
| **Monitoring** | Samba process status, share availability |
| **Recovery** | Service restart + share verification |

#### Backupserver (192.168.52.5) — **THE COMMAND CENTER**
| Aspect | Details |
|---|---|
| **Role** | Orchestration & control plane |
| **Primary Services** | Python orchestrator, Ansible, M/Monit |
| **Secondary Services** | Backup storage, cron daemon, SSH server |
| **Data Stored** | Backup archives, logs, scripts |
| **Monitoring** | M/Monit dashboard, cron logs |
| **Recovery** | Automatic service restart + escalation |

### Layer 2: The Monitoring Stack

```
MONIT AGENTS (Local)
├─ Webserver: Monitors Nginx + disk + network
├─ DBserver: Monitors PostgreSQL + disk + memory
├─ Fileserver: Monitors Samba + disk + connections
└─ Backupserver: Monitors cron + rsync + backup storage
                 ↓
              CENTRAL M/MONIT
                 ├─ Aggregates all Monit alerts
                 ├─ Provides web dashboard
                 └─ Acts as data source for orchestrator
                 ↓
              ORCHESTRATOR (Python)
                 ├─ Queries M/Monit every 5 minutes
                 ├─ Analyzes health status
                 ├─ Triggers recovery playbooks
                 └─ Logs RTO metrics
```

### Layer 3: The Recovery System

#### Ansible Architecture

```
DR Orchestrator (Python)
    ↓ (triggers on failure)
Ansible Playbook Selection
    ├─ recover_postgres.yml
    ├─ recover_nginx.yml
    ├─ recover_fileserver.yml
    ├─ recover_backupserver.yml
    └─ recover_disk.yml
    ↓ (executes via SSH)
Target Hosts (Remote)
    ├─ webserver (via SSH from backupserver)
    ├─ dbserver (via SSH from backupserver)
    └─ fileserver (via SSH from backupserver)
    ↓ (systemctl or admin commands)
Service Recovery
    ├─ Restart service
    ├─ Wait for boot completion
    ├─ Verify connectivity
    └─ Update status in logs
```

#### Playbook Flow (Example: PostgreSQL Recovery)

```
1. Orchestrator detects PostgreSQL down
        ↓
2. Playbook: recover_postgres.yml starts
        ├─ SSH to dbserver
        ├─ Run: systemctl restart postgresql
        └─ Wait 10 seconds for boot
        ↓
3. Verification Phase (3 attempts)
        ├─ Attempt 1: pg_isready check
        ├─ Attempt 2: psql connection test
        ├─ Attempt 3: Query system tables
        └─ All 3 must pass
        ↓
4. Calculate RTO (Recovery Time Objective)
        ├─ Time from detection to healthy = RTO
        ├─ Log: "[SUCCESS] PostgreSQL recovered in 14.2s"
        └─ Send alert email (if enabled)
```

### Layer 4: The Orchestration Engine

#### The 5-Minute Cycle

```
┌─────────────────────────────────────────────────────┐
│  EVERY 5 MINUTES (via cron)                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. HEALTH CHECK (30 seconds)                       │
│     ├─ Query M/Monit dashboard                      │
│     ├─ Check each service status                    │
│     ├─ Verify disk space on all hosts               │
│     └─ Parse results into health dict               │
│                                                     │
│  2. DIAGNOSIS (10 seconds)                          │
│     ├─ Analyze which services are down              │
│     ├─ Determine failure type                       │
│     └─ Select appropriate playbook                  │
│                                                     │
│  3. REMEDIATION (30-60 seconds)                     │
│     ├─ IF problems found:                           │
│     │  ├─ Start timer (t0)                          │
│     │  ├─ Run recovery playbook                     │
│     │  └─ Stop timer (t1)                           │
│     └─ IF no problems:                              │
│        └─ Log "All systems healthy" + exit          │
│                                                     │
│  4. VERIFICATION (45 seconds)                       │
│     ├─ Re-check health 3 times                      │
│     ├─ Wait 3 seconds between checks                │
│     ├─ Collect RTO = (t1 - t0)                      │
│     └─ If still down after 3 retries: escalate      │
│                                                     │
│  5. NOTIFICATION (5 seconds)                        │
│     ├─ Log results to dr_alerts.log                 │
│     ├─ Send email if enabled                        │
│     └─ Update metrics                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Scenario 1: Normal Operation (No Failures)

```
TIME 14:32:00 (5-min cycle starts)
    ↓
M/Monit sees: All 4 hosts GREEN
    ↓
Orchestrator queries M/Monit
    ↓
Result: "All systems healthy"
    ↓
Log: "[INFO] All systems healthy at 14:32:00"
    ↓
Exit (wait 5 minutes, repeat)
```

### Scenario 2: Service Failure & Automatic Recovery

```
TIME 14:32:00 ──────────────────────────────────────────────
    ↓
NGINX CRASHES on webserver
    └─ Some external cause (OOM, config issue, etc.)
    ↓
14:32:03 (Monit detects)
    └─ Monit agent on webserver sees nginx down
    └─ Monit sends alert to M/Monit
    ↓
14:32:05 (Orchestrator runs)
    └─ Health check queries M/Monit
    └─ M/Monit reports: webserver nginx DOWN
    ↓
14:32:06 (Diagnosis)
    └─ Orchestrator determines: "Nginx failure"
    └─ Selects playbook: recover_nginx.yml
    ↓
14:32:07 (Recovery starts)
    └─ Runs: ansible-playbook recover_nginx.yml
    └─ Target: webserver
    └─ Action: systemctl restart nginx
    ↓
14:32:09 (Nginx restarts)
    └─ Service boots up
    └─ Begins accepting connections
    ↓
14:32:12 (Verification phase 1/3)
    └─ Orchestrator: curl -s http://webserver/health
    └─ Response: HTTP 200 OK ✅
    ↓
14:32:15 (Verification phase 2/3)
    └─ Double-check: systemctl status nginx
    └─ Status: active (running) ✅
    ↓
14:32:18 (Verification phase 3/3)
    └─ Final check: nginx -t (config test)
    └─ Result: syntax is ok ✅
    ↓
14:32:19 (RTO Calculation)
    └─ Total time = 14:32:19 - 14:32:07 = 12 seconds
    └─ Log: "[SUCCESS] Nginx recovered in 12.1 seconds"
    ↓
14:32:20 (Notification)
    └─ Email alert sent to ops (if enabled)
    └─ System fully operational again
```

### Scenario 3: Disk Full & Emergency Cleanup

```
TIME 14:37:00 ──────────────────────────────────────────────
    ↓
CRON BACKUP creates huge file
    └─ Database backup grows to 95 GB (limit: 100 GB)
    ↓
14:37:05 (Monit detects)
    └─ Monit on backupserver: df -h shows <5% free
    └─ Alert sent to M/Monit: "Critical disk space"
    ↓
14:37:10 (Orchestrator runs)
    └─ Queries M/Monit
    └─ Sees: "Backupserver disk critically low"
    ↓
14:37:11 (Diagnosis)
    └─ Orchestrator: "Disk space issue"
    └─ Selects playbook: recover_disk.yml
    ↓
14:37:12 (Recovery Phase 1: Normal Cleanup)
    └─ Runs: recover_disk.yml
    └─ Action: Delete backups older than 14 days
    └─ Freed space: 15 GB
    ↓
14:37:35 (After cleanup)
    └─ Check: df -h
    └─ Result: 30 GB free now ✅
    ↓
14:37:40 (Verification)
    └─ Recheck disk: "OK (30% free)"
    └─ Log: "[SUCCESS] Disk recovered in 28 seconds"
    ↓
14:37:42 (Complete)
    └─ System back to healthy state
    └─ Backups can resume normally
```

**But what if cleanup didn't work?**

```
14:37:50 (Verification fails)
    └─ Disk still < 1 GB free
    └─ Log: "[CRITICAL] Disk still critical after cleanup"
    ↓
14:37:51 (Escalation to Emergency)
    └─ Runs: recover_disk_emergency.yml
    └─ Action: DELETE EVERYTHING except 3 newest backups
    └─ Freed space: 80 GB
    ↓
14:38:05 (After emergency)
    └─ Check: df -h
    └─ Result: 80 GB free now ✅
    ↓
14:38:10 (Final Verification)
    └─ Disk healthy
    └─ Log: "[WARNING] Emergency disk cleanup performed"
    └─ Alert email: "Disk space crisis narrowly averted"
```

---

## Failure Detection Strategy

### What We Monitor

| Component | Check Type | Detection Method | Interval |
|---|---|---|---|
| **Nginx** | Service process | `systemctl is-active nginx` | 5 min |
| **Nginx** | HTTP response | `curl -s http://localhost/` | 5 min |
| **PostgreSQL** | Connection | `pg_isready` | 5 min |
| **PostgreSQL** | Query response | SELECT from system table | 5 min |
| **Samba** | Process status | `systemctl is-active smbd` | 5 min |
| **Samba** | Share access | Test share mount/access | 5 min |
| **Disk Space** | Free space | `df -h` on all hosts | 5 min |
| **Backup Services** | Cron logs | Check recent cron executions | 5 min |
| **Backupserver** | Rsync status | Verify rsync processes | 5 min |

### Detection Logic

```python
def check_health():
    """
    Multi-level detection prevents false positives
    """
    
    # Level 1: Query M/Monit (single source of truth)
    status = query_mmonit_api()
    
    # Level 2: Parse alerts
    problems = []
    if status['nginx'] != 'OK':
        problems.append('nginx_down')
    if status['postgresql'] != 'OK':
        problems.append('postgresql_down')
    if status['disk'] < MIN_FREE_DISK:
        problems.append('disk_critical')
    
    # Level 3: Require confirmation (no single-check failures)
    confirmed_problems = []
    for problem in problems:
        # Wait 3 seconds, recheck
        retry_count = 0
        while retry_count < 3:
            if verify_problem_still_exists(problem):
                retry_count += 1
            sleep(3)
        
        # Only report if seen 3 times
        if retry_count >= 3:
            confirmed_problems.append(problem)
    
    return confirmed_problems
```

This approach prevents **false positive** recoveries from transient network issues.

---

## Recovery Mechanisms

### Standard Recovery (Most Services)

```python
def recover_service(service_name):
    """
    1. Detection → 2. Diagnosis → 3. Remediation → 4. Verification
    """
    
    # Step 1: Record start time
    start_time = time.time()
    
    # Step 2: Run Ansible playbook
    playbook = f"ansible/recover_{service_name}.yml"
    result = run_ansible_playbook(playbook)
    
    if result.returncode != 0:
        log_error(f"Recovery failed for {service_name}")
        send_alert_email(f"CRITICAL: {service_name} recovery FAILED")
        return False
    
    # Step 3: Wait for service to fully boot
    sleep(10)
    
    # Step 4: Verify service is healthy (3 attempts)
    for attempt in range(1, 4):
        if verify_service_healthy(service_name):
            rto = time.time() - start_time
            log_success(f"{service_name} recovered in {rto:.1f}s")
            return True
        sleep(3)
    
    # All 3 attempts failed
    log_critical(f"Service {service_name} verification failed")
    send_alert_email(f"CRITICAL: {service_name} still unhealthy")
    return False
```

### Disk Space Recovery (Two-Stage)

```
Stage 1: Normal Cleanup
  └─ Delete backups older than 14 days
  └─ Expected to free 10-30 GB
  
  If successful:
    └─ Return to normal operation
  
  If disk still critical (< 1 GB):
    ↓
Stage 2: Emergency Cleanup (DESTRUCTIVE)
  └─ Delete EVERYTHING except 3 newest backups
  └─ Expected to free 50-100 GB
  ⚠️  WARNING: This deletes old backups
  
  If successful:
    └─ Log WARNING
    └─ Send alert: "Emergency cleanup performed"
  
  If still critical:
    └─ CRITICAL ERROR
    └─ Stop recovery (manual intervention needed)
```

---

## Security Architecture

### Authentication & Authorization

| Layer | Mechanism | Security Level |
|---|---|---|
| **SSH Keys** | ED25519 public-key auth | ⭐⭐⭐⭐⭐ (highest) |
| **Passwords** | None in automation scripts | ⭐⭐⭐⭐⭐ |
| **Sudo Access** | NOPASSWD for automation user | ⭐⭐⭐⭐ (controlled via sudoers) |
| **Email Creds** | Environment variables only | ⭐⭐⭐⭐ (not in code) |
| **M/Monit** | Default credentials (should change) | ⭐⭐ (admin/swordfish) |

### Network Isolation

```
┌────────────────────────────────────────────┐
│  SECURE: Host-only Network                 │
│  (192.168.52.0/24)                         │
│  ├─ Only accessible from hypervisor        │
│  ├─ No internet exposure                   │
│  └─ No inbound traffic from outside        │
└────────────────────────────────────────────┘
```

### Data Protection

| Data Type | At Rest | In Transit | Backup |
|---|---|---|---|
| **Database (PII)** | Encrypted disk | SSH/TLS | Optional encryption |
| **Configs** | Filesystem perms | SSH | Versioned + backed up |
| **Logs** | Limited permissions | SSH/syslog | Archived + rotated |
| **Credentials** | Env vars (not files) | Not transmitted | Not backed up |

---

## Scalability & Limits

### Current Architecture (4 Hosts)

| Metric | Current | Limit | Headroom |
|---|:---:|:---:|:---:|
| **Monitored Hosts** | 4 | ~20 | Good |
| **Health Checks/Min** | 4 × 10 checks = 40 | ~500 | Good |
| **Backup Frequency** | 2×/day (DB), 1×/day (files) | ~100/day | Excellent |
| **Log Storage** | ~500 MB/month | ~10 GB/month | Adequate |
| **M/Monit Dashboard** | 4 hosts | 50-100 | Excellent |

### Scaling Beyond 4 Hosts

To add more servers, you would:

1. **Create new VM** with appropriate role
2. **Update Ansible inventory** with new host IP
3. **Copy SSH public key** to new host
4. **Add to M/Monit configuration** for monitoring
5. **Test connectivity** with `ansible -i inventory.ini all -m ping`

**Limitation:** The backupserver is a single point of control. For >20 hosts, consider:
- Separate orchestrator for each zone
- Distributed Monit/M/Monit setup
- Load-balanced backup servers

---

## Technical Debt & Future Improvements

### Known Limitations

- ✅ Single backupserver (risk if it fails)
- ✅ Synchronous orchestration (one failure at a time)
- ✅ Manual escalation for multi-host failures
- ✅ No redundant storage for backups
- ✅ M/Monit credentials need to be changed

### Potential Enhancements

**Phase 1 (Logging & Alerts)**
- JSON structured logs for parsing
- Email alerts for critical events
- Slack/Teams integration

**Phase 2 (Redundancy)**
- Secondary backupserver (active/passive)
- Distributed backup storage
- Multi-region replication

**Phase 3 (Intelligence)**
- Machine learning anomaly detection
- Predictive failure forecasting
- Intelligent playbook selection

**Phase 4 (Compliance)**
- HIPAA-compliant audit logs
- Encryption at rest & in transit
- Compliance reporting dashboard

---

## Reading Guide

| I Want to Understand... | Read This Section |
|---|---|
| How the system detects failures | [Failure Detection Strategy](#failure-detection-strategy) |
| How recovery actually works | [Recovery Mechanisms](#recovery-mechanisms) |
| What happens during a failure | [Data Flow Diagrams](#data-flow-diagrams) |
| The 4-host topology | [Component Layers → The Four Nodes](#layer-1-the-four-nodes) |
| Security implications | [Security Architecture](#security-architecture) |

---

**Next Steps:**
- Read [SETUP_GUIDE.md](SETUP_GUIDE.md) to build this system
- See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for operational details
- Check [README.md](../README.md) for quick-start examples
