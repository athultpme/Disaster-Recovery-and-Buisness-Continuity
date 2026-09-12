# Disaster Recovery and Business Continuity: Simulated Healthcare Infrastructure

**Course:** Disaster Recovery and Business Continuity  
**Institution:** University of Applied Sciences  
**Instructor:** Prof. Igor Tomičić  
**Submission Date:** September 2026

## Team

| Name | Role |
|---|---|
| Athul Thuvattu Paramabth | Team Lead / Project Manager |
| Thattarakkal Vishnu Viswanath | Virtual Infrastructure Engineer |
| Varghese Kuruvilla | Backup and Recovery Specialist |
| Anantha Krishnan Anil Kumar | Monitoring and Automation Developer |

## Overview

This project presents a self-healing disaster recovery and business continuity system designed for a simulated four-server healthcare infrastructure. The system automatically detects and recovers from common failure modes across web, database, file, and backup servers using coordinated monitoring, orchestration, and playbook-driven recovery.

**Key Capabilities:**
- Automated failure detection via Monit agents across all infrastructure nodes
- Centralized orchestration and recovery coordination from a dedicated backup server
- Recovery playbooks for six critical failure scenarios (PostgreSQL, Nginx, Samba, backup, and disk failures)
- Integrated backup and point-in-time recovery for all stateful services

## Architecture

```
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│   webserver     │  │   dbserver       │  │  fileserver     │
│   (Nginx)       │  │ (PostgreSQL)     │  │   (Samba)       │
│ Monit Agent     │  │  Monit Agent     │  │  Monit Agent    │
└────────┬────────┘  └────────┬─────────┘  └────────┬────────┘
         │                    │                      │
         └────────────────────┼──────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │ backupserver       │
                    │ • M/Monit Central  │
                    │ • Orchestrator     │
                    │ • Ansible          │
                    │ • Backup Storage   │
                    │  (/backup)         │
                    └────────────────────┘
```

Each infrastructure node runs a local Monit agent reporting to the M/Monit dashboard on the backup server. The backup server orchestrates recovery actions via Ansible and can trigger automated responses through Monit exec actions. The orchestrator runs on a 5-minute cycle, performing health checks and initiating recovery workflows as needed.

## Repository Structure

```
.
├── ansible/           # Playbooks for recovery and configuration
├── scripts/           # Orchestration, backup, and simulation tools
│   ├── backup/        # Scheduled backup routines (cron-triggered)
│   ├── restore/       # Manual restore scripts
│   ├── monitoring/    # Health-check automation
│   └── dr/            # Orchestrator and disaster simulator
├── monit/             # M/Monit integration and auto-trigger configuration
├── docs/              # Deployment and operational guides
└── README.md
```

## Getting Started

**Start here:** [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)

This is a complete, step-by-step runbook for building the entire system from bare virtual machines, including:

1. Virtual machine provisioning (4 Ubuntu VMs)
2. Required software installation per host
3. Passwordless SSH configuration for Ansible and Monit
4. Deployment of automation and playbooks
5. Cron scheduling for backups and the orchestrator
6. M/Monit systemd configuration
7. Monit exec trigger configuration per host
8. End-to-end testing with `scripts/disaster_sim143.py`

**Supplementary guides:**
- [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) — Ansible deployment and cron scheduling details
- [monit/MONIT_AUTOTRIGGER_GUIDE.md](monit/MONIT_AUTOTRIGGER_GUIDE.md) — M/Monit setup and exec action wiring
- [docs/Final_Project_Report.docx](docs/Final_Project_Report.docx) — Complete project report with measured results and evidence from live testing

## Failure Detection and Recovery

The orchestrator monitors six categories of failures and executes targeted recovery actions:

| Failure Type | Detection Method | Recovery Action |
|---|---|---|
| PostgreSQL Service Down | `pg_isready` via SSH | `recover_postgres.yml` |
| Nginx Service Down | `systemctl is-active`; fallback to HTTP probe | `recover_nginx.yml` |
| Samba/File Server Down | `systemctl is-active smbd` via SSH | `recover_fileserver.yml` |
| Backup Server Unhealthy | Verify cron, rsync, and `/backup` availability | `recover_backupserver.yml` |
| Low Disk Space (any host) | Remote `df` over SSH to all 4 hosts | `recover_disk.yml` + emergency escalation |
| Disk Space Emergency | Retain if all mitigations fail | `recover_disk_emergency.yml` + Python failsafe |

All health checks retry before being marked as failed (avoiding false alarms from transient network delays). Recovery actions enforce a settle period before re-verification to allow services time to stabilize.

## Testing Failures On-Demand

The disaster simulator allows targeted failure injection for testing:

```bash
# Inject a specific failure
python3 scripts/disaster_sim143.py disk
python3 scripts/disaster_sim143.py nginx
python3 scripts/disaster_sim143.py postgresql

# List available failures
python3 scripts/disaster_sim143.py --list

# Inject a random failure (default behavior)
python3 scripts/disaster_sim143.py
```

## Operational Assumptions

- **Topology:** Four Ubuntu VMs (webserver, dbserver, fileserver, backupserver)
- **Orchestration:** SSH + Ansible from backup server to other hosts
- **Canonical Orchestrator:** `scripts/dr_orchestrator143.py` (primary implementation)
- **Legacy Scripts:** `dr_orchestrator.py`, `dr_orchestrator1.py`, `dr_orchestrator123.py` are historical; use only if explicitly required
- **Backup and Script Paths:** Anchored at `/backup/scripts/` on the backup server
- **Inventory:** Defined in `ansible/inventory.ini`

## Code Conventions

When modifying automation in this repository:

1. **Preserve the orchestration flow.** Keep changes small and explicit; avoid architectural rewrites without justification.
2. **Respect host safety.** Use idiomatic SSH and Ansible commands; do not hardcode hostnames or paths unless the existing script already does so.
3. **Follow logging patterns.** Maintain consistency with existing logging and backup file naming conventions.
4. **Validate before claiming readiness:**
   ```bash
   ansible -i ansible/inventory.ini all -m ping
   python3 -m py_compile scripts/*.py
   bash -n scripts/*.sh
   ```

## Known Limitations

- **Unified backup retention:** `backup_postgresql.sh`, `backup_dbpostgre.py`, and file/web server backup scripts each maintain separate retention schedules. Consider consolidating to a single canonical backup method for PostgreSQL.
- **Disk failsafe assumption:** The disk recovery logic currently targets `/backup/full.disk` (the simulated failure artifact). In production, replace or extend this with domain-specific logic for your actual disk-filling processes.
- **Monit default credentials:** The M/Monit dashboard uses default admin credentials. Change these before deploying beyond a lab environment (see `monit/MONIT_AUTOTRIGGER_GUIDE.md`).

## Validation and Verification Commands

Verify Ansible connectivity and playbook execution:

```bash
ansible -i ansible/inventory.ini all -m ping
ansible-playbook -i ansible/inventory.ini setup_web.yml
ansible-playbook -i ansible/inventory.ini healthcare.yml
ansible-playbook -i ansible/inventory.ini recover_postgres.yml
ansible-playbook -i ansible/inventory.ini recover_nginx.yml
ansible-playbook -i ansible/inventory.ini recover_fileserver.yml
ansible-playbook -i ansible/inventory.ini recover_backupserver.yml
ansible-playbook -i ansible/inventory.ini recover_disk.yml
```

Validate Python and shell scripts:

```bash
python3 -m py_compile scripts/*.py
bash -n scripts/*.sh
```

## Project Scope and Language Composition

This project is written primarily in **Python (91.7%)** for orchestration and simulation, with **Shell scripting (8.3%)** for backup automation and system integration. It is infrastructure-focused, not a typical application service; all changes should prioritize production safety and adhere to the operational documentation.

---

**For complete implementation details, see [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).**
