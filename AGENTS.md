# AGENTS.md

This repository is a disaster-recovery and business-continuity lab for a 4-node Ubuntu VM environment. Most work here is infrastructure automation, not a typical application service, so follow the repo’s operational docs and prefer minimal, production-safe changes.

## Project map

- `ansible/`: deployment and recovery playbooks for web, PostgreSQL, file server, backup server, and disk recovery.
- `scripts/`: automation scripts for backup, restore, monitoring, and DR orchestration.
- `docs/`: operational docs for setup, implementation, and operational troubleshooting.
- `monit/`: Monit/M/Monit integration and auto-trigger configuration guidance.

## Key references

- [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)
- [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)
- [monit/MONIT_AUTOTRIGGER_GUIDE.md](monit/MONIT_AUTOTRIGGER_GUIDE.md)

## Operating assumptions

- The production topology is four hosts: `webserver`, `dbserver`, `fileserver`, and `backupserver`.
- Backup/DR orchestration runs from the backup server and uses SSH + Ansible to reach the other hosts.
- The canonical orchestrator in this repo is `scripts/dr_orchestrator143.py`; `scripts/dr_trigger.sh` expects that implementation.
- There are several legacy variants such as `dr_orchestrator.py`, `dr_orchestrator1.py`, and `dr_orchestrator123.py`; treat them as historical unless a task explicitly calls for them.
- Most scripts depend on `/backup/...` paths and the inventory at `ansible/inventory.ini`.

## Code conventions for agents

- Prefer small, explicit changes that preserve the existing automation flow.
- Keep SSH, `sudo`, and Ansible commands idiomatic and host-safe; do not hardcode hostnames/paths unless the existing script already does so.
- Preserve logging patterns and backup file naming conventions already used by the scripts.
- When modifying infrastructure automation, validate syntax and execution paths before claiming readiness.

## Validation commands

Use the repo’s existing commands for verification:

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

For Python and shell script changes, use:

```bash
python3 -m py_compile scripts/*.py
bash -n scripts/*.sh
```

## Workflow guidance

- If a change affects recovery logic, read the orchestrator and the relevant playbook together before patching.
- If a change affects monitoring or alerting, review the Monit guide and the DR trigger flow together.
- If a task concerns setup or topology, consult [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) before editing automation.
- Keep doc updates brief and linked rather than duplicating operational detail already captured in the existing guides.

## Important caveats

- Some docs mention older filenames and commands; use the repo state, not stale examples, as the source of truth.
- The project is sensitive to host networking and permissions. Avoid changing SSH trust, sudoers, or cron assumptions without checking the setup guide.
- If a fix targets disk recovery escalation, confirm the change still aligns with `recover_disk.yml` and `recover_disk_emergency.yml` behavior.
