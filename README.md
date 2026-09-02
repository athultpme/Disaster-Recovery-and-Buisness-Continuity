# Disaster Recovery & Buisness Continuity - Simulated Healthcare Infrastructure 

**Course:** Disaster Recovery and Buiness Continuity
**Professor:** Prof Igor Tomičić
**Submitted:** September 2026

## Team
| Name | Role |
|---|---|
| Athul Thuvattu Paramabth | Team Leader / Project Manager|
| Thattarakkal Vishnu Viswanath | Virtual Infrastructure Engineer |
| Varghese Kuruvilla | Backup and Recovery Specialist|
| Anantha Krishnan Anil Kumar | Monitoring and Automation Developer |

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Setup](#setup)
- [Testing a Specific Failure on Demand](#testing-a-specific-failure-on-demand)
- [What the Orchestrator Checks and Recovers](#what-the-orchestrator-checks-and-recovers)
- [Documentation](#documentation)
- [Known Limitation](#known-limitation--things-to-keep-an-eye-on)

## Overview
A self-healing disaster recovery system for a simulated 4-server environment (web, database, file, and backup servers), built as a Disaster Recovery and Buisness Continuity project. Automated backups, health monitoring via Monit/M-Monit, and an orchestrator that detects failures and runs targeted Ansible playbooks to recover - with a built-in Python failsafe for disk-space recovery that doesn't depend on the Ansible layer alone.

## Architecture

```
_______________        ________________      _______________
| webserver    |       |  dbserver     |     |fileserver    |
| (nginx)      |       |(PostgreSQL)   |     |(Samba)       |
|______________|       |_______________|     |______________|
    | Monit agent, reports to M/Monit           |              
    |________________________________________                           
                        _______|______________       
                        | backupserver       |
                        | - M/Monit          |         
                        | - dr_orchestrator.py                   
                        | - Ansible Pplaybook                   
                        | - backup storage (/backup)                   
                        |                    |
                        |____________________|
```

Each host runs a local Monit agent that reports to the M/Monit dashboard on `backupserver` and can trigger immediate recovery via `exec` actions. `backupserver` also runs `dr_orchestrator.py` on a 5-minute cron schedule as a second, independent safety net.

## Directory structure

```
scripts/ 
  backup/       # scheduled backup scripts (cron), one per service
  restore/      # manual restore scripts, run on demand
  monitoring/   # standalone health-check script for the DB backup
  dr/           # orchestrator, trigger entrypoint, disaster simulator
ansible/        # inventory + one recovery playbook per failure type
monit/          # systemd unit for M/Monit + guide for wiring
auto-triggers
docs/           # deployment walkthrough
```

## Setup

**Start with `docs/SETUP_GUIDE.md`** It's a complete, linear runbook for building this entire system from bare virtual machines - required software per host, SSH trust in both directions, sudoers configuration, Ansible deployment, Monit wiring, cronscheduling, and a full verification sequence with expected results.

`docs/IMPLEMENTATION_GUIDE.md` and `monit/MONIT_AUTOTRIGGER_GUIDE.md`
go deeper on the Ansible and Monit layers specifically, and are referenced from within the setup guide at the relevant steps.

Quick summary of what the setup guide covers:
1. Set up four virtual machines in virtual box (web server, databse server, file server, and backup server) and install tools required.
2. Set up passwordless SSH from `backupserver` to the other three hosts (Ansible needs this) and from each host back to `backupserver` (Monit's exec actions need this, opposite direction).
3. Deploy `ansible/*` to `backupserver:/backup/scripts/` (backup/restore scripts run on backupserver and reach out over SSH to the relevant host).
4. Deploy `scripts/*` to `backupserver:/backup/scripts/` (backup/restore scripts run on backupserver and reach out over SSH to the relevant host).
5. Schedule backups and the orchestrator via cron (see IMPLEMENTATION_GUIDE.md)
6. Install `monit/mmonit.service` so M/Monit survives reboots and restarts automatically on crash.
7. Add the exec triggers from `MONIT_AUTOTRIGGER_GUIDE.md` to each host's local Monit config.
8. Run `scripts/disaster_sim143.py` to inject a test failure and confirm end-to-end recovery.

## What the orchestrator checks and recovers

| Failure type | Detection | Recovery playbook |
|---|---|---|
| PostgreSQL down | `pg_isready` over SSH to dbserver | `recover_postgres.yml` |
| Nginx down | `systemctl is-active`, falls back to an HTTP check | `recover_nginx.yml` |
| Samba/file server down |`systemctl is-active smbd` on fileserver | `recover_nginx.yml`|
| Backup server unhealthy | `cron` + `rsync` active, `/backup` exists | `recover_backupserver.yml` |
| Low disk space (any host) | remote `df` over SSH, all 4 hosts | `recover_disk.yml`, escalating to `recover_disk_emergency.yml`, then a built-in Python failsafe that removes the known disk-filler file directly over SSH regardless of playbook state |

Each check retries before being trusted (avoids false alarms from a single slow SSH response), and there's a settle period after a recovery action before the orchestrator re-verifies (avoids reporting a service as "still down" while it's mid-restart).

## Known limitation / things to keep an eye on
- Backup retention across scripts isn't unified - `backup_postgresql.sh`, `backup_dbpostgre.py`, and the fileserver/webserver scripts each keep their own schedule. Pick one canonical DB backup method rather than running both.
- The disk failsafe currently assumes the simulated failure file is `/backup/full.disk` (from `disaster_sim143.py`). In a non-simulated environment, replace or extend this with logic specific to your real disk-uasge patterns.
Monit's default admin credentials should be changed before this goes anywhere beyond a lab environment - see `monit/MONIT_AUTOTRIGGER_GUIDE.md`

## Testing a specific failure on demand
`disaster_sim143.py` originally only picked a random failure. It now accept a target:
```bash
python3 scripts/disaster_sim143.py disk
python3 scripts/disaster_sim143.py nginx
python3 scripts/disaster_sim143.py postgresql
python3 scripts/disaster_sim143.py --list
```
Run with no argument for the original random behavior.

## Documentation
- `docs/SETUP_GUIDE.md` - **start here** - complete from-scratch build instructions.
-`docs/IMPLEMENTAION_GUIDE.md` - deployment walkthrough for the Ansible/backup layer.
- `docs/Final_Project_Report.docx` - the complete project report, covering all required project phases with measured test results and screenshot evidence for every failure type.
