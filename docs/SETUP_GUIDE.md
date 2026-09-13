# 🛠️ Complete Setup Guide

**Build a Production-Grade DR/BC System from Scratch**

> This guide provides step-by-step instructions to implement a self-healing infrastructure on 4 fresh Ubuntu VMs. No prior experience needed—each command has been tested on actual systems.

---

## 📋 Table of Contents

1. [System Architecture](#-system-architecture)
2. [Prerequisites & Planning](#-prerequisites--planning)
3. [Phase 1: Host Preparation](#phase-1-host-preparation)
4. [Phase 2: Network & SSH Configuration](#phase-2-network--ssh-configuration)
5. [Phase 3: Ansible Deployment](#phase-3-ansible-deployment)
6. [Phase 4: Monitoring & Orchestration](#phase-4-monitoring--orchestration)
7. [Phase 5: Testing & Validation](#phase-5-testing--validation)
8. [Verification Checklist](#-verification-checklist)
9. [Troubleshooting](#-troubleshooting)

---

## 🏗️ System Architecture

### The Four Servers

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR NETWORK (192.168.52.0/24)           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🌐 WEBSERVER (192.168.52.3)                                │
│  │  └─ Role: Web application tier                           │
│  │  └─ Software: Nginx + Monit agent                        │
│  │  └─ Username: webserver                                  │
│                                                               │
│  🗄️  DBSERVER (192.168.52.4)                                │
│  │  └─ Role: Database tier                                  │
│  │  └─ Software: PostgreSQL 16 + Monit agent               │
│  │  └─ Username: dbserver                                   │
│                                                               │
│  📁 FILESERVER (192.168.52.6)                               │
│  │  └─ Role: File storage tier                              │
│  │  └─ Software: Samba + Monit agent                        │
│  │  └─ Username: fileserver                                 │
│                                                               │
│  💾 BACKUPSERVER (192.168.52.5)  ← COMMAND CENTER           │
│     └─ Role: Central orchestration & backup                 │
│     └─ Software: Ansible + Python + M/Monit                │
│     └─ Username: backupserver                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow
```
All Servers → Monit Agents → M/Monit Dashboard (Central)
                                      ↓
                        Orchestrator (runs every 5 min)
                                      ↓
                        Ansible Playbooks (recovery)
                                      ↓
                        Email Alerts + Logging
```

---

## 📋 Prerequisites & Planning

### Hardware Requirements

| Requirement | Minimum | Recommended |
|---|:---:|:---:|
| **Hypervisor** | VirtualBox 6.0+ | Proxmox VE 7.0+ |
| **CPU Cores** | 8 logical cores | 16+ cores |
| **RAM** | 16 GB | 32 GB |
| **Storage** | 200 GB | 500 GB SSD |
| **Network** | Host-only network | Dedicated VLAN |

**⚠️ Critical:** Under-provisioning CPU/RAM causes kernel lockups under monitoring load. See README.md for details.

### Network Planning

| Item | Your Value | Notes |
|---|---|---|
| **Network Subnet** | 192.168.52.0/24 | Can change; update all IPs consistently |
| **Webserver IP** | 192.168.52.3 | Static, set in Ubuntu netplan |
| **DBserver IP** | 192.168.52.4 | Static, set in Ubuntu netplan |
| **Fileserver IP** | 192.168.52.6 | Static, set in Ubuntu netplan |
| **Backupserver IP** | 192.168.52.5 | Static, set in Ubuntu netplan |
| **Gateway** | 192.168.52.1 | Route traffic out (if needed) |
| **DNS** | 8.8.8.8 | For package downloads |

### Account Planning

On each VM, create a standard user matching the hostname:

```bash
# User naming convention (required for Ansible)
webserver VM  → username: webserver
dbserver VM   → username: dbserver
fileserver VM → username: fileserver
backupserver VM → username: backupserver
```

**Why this naming?** The Ansible inventory uses these exact usernames for SSH connections.

---

## Phase 1: Host Preparation

### Step 1.1: Create VMs

Create 4 Ubuntu Server 22.04 LTS VMs (or 24.04):
- 2 CPU cores per VM minimum (4 recommended)
- 4 GB RAM per VM minimum (8 recommended)
- 50 GB disk per VM
- Host-only network adapter (same network for all)

### Step 1.2: Initial System Setup (All Hosts)

Run these commands on **each of the 4 VMs**:

```bash
# Update package lists and install core utilities
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl wget git net-tools vim htop

# Set static hostname (replace with actual hostname)
sudo hostnamectl set-hostname webserver  # ← change for each VM
```

### Step 1.3: Create Non-Root User (All Hosts)

Replace `webserver` with the appropriate username for each VM:

```bash
# Create user with home directory and sudo access
sudo useradd -m -s /bin/bash webserver
sudo usermod -aG sudo webserver

# Set password (make it strong)
sudo passwd webserver

# Verify user was created
id webserver
```

### Step 1.4: Configure Static IP (All Hosts)

Edit `/etc/netplan/00-installer-config.yaml`:

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Replace with (adjust `addresses` for each VM):

```yaml
# For Webserver (192.168.52.3)
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - 192.168.52.3/24
      gateway4: 192.168.52.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

Apply changes:

```bash
sudo netplan apply
ip addr show  # Verify static IP assigned
```

---

## Phase 2: Network & SSH Configuration

### Step 2.1: Verify Network Connectivity

From your workstation, verify all 4 servers are reachable:

```bash
ping -c 2 192.168.52.3  # webserver
ping -c 2 192.168.52.4  # dbserver
ping -c 2 192.168.52.5  # backupserver
ping -c 2 192.168.52.6  # fileserver
```

All should reply. If any timeout, fix networking before continuing.

### Step 2.2: Generate SSH Keys (Backupserver)

**On backupserver VM**, create SSH key for passwordless login to other hosts:

```bash
# Switch to backupserver user
sudo su - backupserver

# Generate ED25519 key (modern, secure)
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

# Verify key was created
ls -la ~/.ssh/
```

### Step 2.3: Copy Public Key to Other Hosts (Backupserver → Others)

**Still on backupserver**, copy your public key to each other host:

```bash
# Copy to webserver
ssh-copy-id -i ~/.ssh/id_ed25519.pub webserver@192.168.52.3

# Copy to dbserver
ssh-copy-id -i ~/.ssh/id_ed25519.pub dbserver@192.168.52.4

# Copy to fileserver
ssh-copy-id -i ~/.ssh/id_ed25519.pub fileserver@192.168.52.6

# When prompted: type the password for each user
```

### Step 2.4: Verify Bidirectional SSH (Backupserver)

**Test from backupserver** → other hosts (one direction):

```bash
# Test all three connections in parallel
for host in webserver@192.168.52.3 dbserver@192.168.52.4 fileserver@192.168.52.6; do
  echo "Testing $host..."
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$host" "echo OK from $host"
done

# Expected output:
# OK from webserver@192.168.52.3
# OK from dbserver@192.168.52.4
# OK from fileserver@192.168.52.6
```

If any fail, **stop here** and troubleshoot (see [Troubleshooting](#-troubleshooting)).

### Step 2.5: Configure Return SSH Keys (Other Hosts → Backupserver)

**On each of webserver, dbserver, and fileserver individually:**

```bash
# Generate key for DR trigger alerts
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_dr_trigger

# Copy public key to backupserver's authorized_keys
ssh-copy-id -i ~/.ssh/id_dr_trigger.pub backupserver@192.168.52.5

# Test it works
ssh -i ~/.ssh/id_dr_trigger backupserver@192.168.52.5 "echo OK"
```

### Step 2.6: Configure Passwordless Sudo (All Hosts)

This is **critical**—Ansible hangs without passwordless sudo.

**On all 4 hosts**, add sudoers rule:

```bash
sudo visudo -f /etc/sudoers.d/ansible-nopasswd
```

Add this line (replace `webserver` with the appropriate username):

```
webserver ALL=(ALL) NOPASSWD: ALL
```

Verify it works:

```bash
sudo -l -U webserver  # Should show "(ALL) NOPASSWD: ALL"
```

---

## Phase 3: Ansible Deployment

### Step 3.1: Install Ansible (Backupserver Only)

**On backupserver VM**:

```bash
sudo apt update
sudo apt install -y ansible python3 python3-pip
ansible --version  # Verify installation
```

### Step 3.2: Clone Repository (Backupserver)

```bash
cd ~
git clone https://github.com/athultpme/Disaster-Recovery-and-Buisness-Continuity.git
cd Disaster-Recovery-and-Buisness-Continuity
```

### Step 3.3: Update Ansible Inventory

Edit `ansible/inventory.ini` to match your actual IPs:

```bash
nano ansible/inventory.ini
```

Ensure it matches your VM IPs:

```ini
[webserver]
webserver ansible_host=192.168.52.3 ansible_user=webserver

[dbserver]
dbserver ansible_host=192.168.52.4 ansible_user=dbserver

[fileserver]
fileserver ansible_host=192.168.52.6 ansible_user=fileserver

[backupserver]
backupserver ansible_host=192.168.52.5 ansible_user=backupserver
```

### Step 3.4: Test Ansible Connectivity

**On backupserver**, verify Ansible can reach all hosts:

```bash
ansible -i ansible/inventory.ini all -m ping
```

Expected output:
```
webserver | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
dbserver | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
fileserver | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
backupserver | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

If you see `UNREACHABLE`, fix SSH trust first (Step 2).

### Step 3.5: Run Setup Playbook

Deploy core software and monitoring to all hosts:

```bash
cd ~/Disaster-Recovery-and-Buisness-Continuity

# Dry-run first (safe—doesn't make changes)
ansible-playbook -i ansible/inventory.ini ansible/setup_web.yml --check

# Run for real
ansible-playbook -i ansible/inventory.ini ansible/setup_web.yml
```

This installs:
- Nginx on webserver
- PostgreSQL 16 on dbserver
- Samba on fileserver
- Monit agents on all hosts

### Step 3.6: Install Services Manually (If Playbook Fails)

If Ansible playbook has issues, install manually on each host:

**On webserver:**
```bash
sudo apt update
sudo apt install -y nginx monit
sudo systemctl enable --now nginx
```

**On dbserver:**
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib monit
sudo systemctl enable --now postgresql

# Create healthcare database
sudo -u postgres createdb healthcare_db
```

**On fileserver:**
```bash
sudo apt update
sudo apt install -y samba monit
sudo mkdir -p /uploads
sudo chown fileserver:fileserver /uploads

# Add Samba share
sudo tee -a /etc/samba/smb.conf > /dev/null <<EOF
[uploads]
  path = /uploads
  browseable = yes
  writable = yes
  public = yes
EOF

sudo systemctl enable --now smbd
```

**On backupserver:**
```bash
sudo apt update
sudo apt install -y ansible python3 python3-pip rsync git monit cron
mkdir -p ~/backup/{database,files,webserver,logs,scripts}
chmod 700 ~/backup
```

---

## Phase 4: Monitoring & Orchestration

### Step 4.1: Deploy Backup Directory Structure (Backupserver)

```bash
# Create backup folders
mkdir -p /backup/{database,files,webserver,logs,scripts}

# Set permissions
sudo chown -R backupserver:backupserver /backup
chmod 700 /backup
```

### Step 4.2: Copy Scripts to Backupserver

```bash
# From your workstation or within the cloned repo:
cd ~/Disaster-Recovery-and-Buisness-Continuity

# Copy all scripts
cp scripts/*.py scripts/*.sh /backup/scripts/
cp -r ansible/* /backup/scripts/ansible/

# Make executable
chmod +x /backup/scripts/*.sh /backup/scripts/*.py

# Verify
ls -la /backup/scripts/
```

### Step 4.3: Schedule Automated Tasks (Backupserver)

Edit crontab:

```bash
crontab -e
```

Add these lines:

```bash
# Database backup every 6 hours
0 */6 * * * /usr/bin/python3 /backup/scripts/backup_dbpostgre.py >> /backup/logs/backup_db.log 2>&1

# File server backup nightly at 2 AM
0 2 * * * /bin/bash /backup/scripts/backup_fileserver.sh >> /backup/logs/backup_file.log 2>&1

# Web server config backup nightly at 2:30 AM
30 2 * * * /bin/bash /backup/scripts/backup_webserver.sh >> /backup/logs/backup_web.log 2>&1

# Orchestrator health check every 5 minutes
*/5 * * * * /usr/bin/python3 /backup/scripts/dr_orchestrator143.py >> /backup/logs/cron_dr.log 2>&1
```

Verify crontab was saved:

```bash
crontab -l
```

### Step 4.4: Install M/Monit (Central Dashboard)

Download M/Monit from [mmonit.com](https://mmonit.com):

```bash
# On backupserver, download and extract
cd /tmp
wget https://mmonit.com/download/dist/mmonit-3.7.16-linux-x64.tar.gz
tar xzf mmonit-*.tar.gz

# Move to /opt
sudo mv mmonit-* /opt/mmonit

# Create systemd service
sudo tee /etc/systemd/system/mmonit.service > /dev/null <<'EOF'
[Unit]
Description=M/Monit Monitoring Dashboard
After=network.target

[Service]
Type=forking
ExecStart=/opt/mmonit/bin/mmonit -c /opt/mmonit/conf/mmonit.conf
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable --now mmonit
sudo systemctl status mmonit
```

Access the dashboard at `http://192.168.52.5:8080` (username: `admin`, password: `swordfish` — change this!)

---

## Phase 5: Testing & Validation

### Step 5.1: Verify All Systems Are Healthy

**On backupserver**, run the orchestrator once:

```bash
python3 /backup/scripts/dr_orchestrator143.py
```

Expected output:
```
[INFO] Checking health of all systems...
[OK] webserver: nginx is running
[OK] dbserver: postgresql is running
[OK] fileserver: samba is running
[OK] backupserver: backup services running
[OK] All disks have sufficient space
[SUCCESS] All systems healthy
```

### Step 5.2: Test Individual Recovery Playbooks

**Before trusting the full orchestrator, test each playbook:**

```bash
cd /backup/scripts/ansible

# Test web server recovery
ansible-playbook -i inventory.ini recover_nginx.yml

# Test database recovery
ansible-playbook -i inventory.ini recover_postgres.yml

# Test file server recovery
ansible-playbook -i inventory.ini recover_fileserver.yml
```

Each should complete with no `FAILED` tasks.

### Step 5.3: Inject a Fake Failure & Test Auto-Recovery

**On backupserver**:

```bash
# Simulate PostgreSQL crash
python3 /backup/scripts/disaster_sim143.py postgresql

# Trigger recovery (normally runs via cron)
python3 /backup/scripts/dr_trigger.sh

# Watch recovery in real-time
tail -f /backup/logs/dr_alerts.log
```

Expected output sequence:
```
[14:32:10] [ALERT] PostgreSQL failure detected
[14:32:11] [INFO] Triggering recovery playbook...
[14:32:15] [INFO] Waiting for service to settle...
[14:32:25] [VERIFY] Validation attempt 1/3
[14:32:28] [SUCCESS] Recovery completed in 18.2 seconds
```

### Step 5.4: Test Disk Space Recovery

```bash
# Simulate disk full condition
python3 /backup/scripts/disaster_sim143.py disk

# Trigger orchestrator
python3 /backup/scripts/dr_trigger.sh

# Verify disk cleanup occurred
df -h /backup
```

---

## ✅ Verification Checklist

Run through this checklist to confirm everything is working:

- [ ] **Network**
  - [ ] All 4 VMs have static IPs (ping works)
  - [ ] All VMs can reach each other

- [ ] **SSH**
  - [ ] `ssh webserver@192.168.52.3 "echo OK"` returns OK
  - [ ] `ssh dbserver@192.168.52.4 "echo OK"` returns OK
  - [ ] `ssh fileserver@192.168.52.6 "echo OK"` returns OK

- [ ] **Passwordless Sudo**
  - [ ] `sudo -l -U webserver` shows `NOPASSWD: ALL`
  - [ ] Same for dbserver, fileserver, backupserver users

- [ ] **Services**
  - [ ] `ssh webserver@192.168.52.3 "systemctl is-active nginx"` returns `active`
  - [ ] `ssh dbserver@192.168.52.4 "systemctl is-active postgresql"` returns `active`
  - [ ] `ssh fileserver@192.168.52.6 "systemctl is-active smbd"` returns `active`

- [ ] **Ansible**
  - [ ] `ansible -i ansible/inventory.ini all -m ping` → all return `SUCCESS`

- [ ] **Orchestrator**
  - [ ] `python3 /backup/scripts/dr_orchestrator143.py` → no errors
  - [ ] Crontab has orchestrator scheduled (`crontab -l`)

- [ ] **Recovery Testing**
  - [ ] Manual recovery playbooks work without errors
  - [ ] Disaster injection + recovery cycle completes successfully
  - [ ] Logs show recovery times in `/backup/logs/dr_alerts.log`

---

## 🔧 Troubleshooting

### SSH Connection Refused

**Symptom:** `Connection refused` when trying SSH

**Solution:**
```bash
# 1. Verify SSH service is running on target
ssh target@IP "sudo systemctl status ssh"

# 2. Check SSH configuration
ssh target@IP "sudo sshd -t"  # syntax check

# 3. Restart SSH service
ssh target@IP "sudo systemctl restart ssh"
```

### Ansible Says "UNREACHABLE"

**Symptom:** Ansible returns `UNREACHABLE` or `0 hosts matched`

**Solution:**
```bash
# 1. Test SSH manually first
ssh webserver@192.168.52.3 "whoami"

# 2. Verify inventory.ini IPs and usernames match actual VMs
cat ansible/inventory.ini

# 3. Test Ansible connectivity with verbose output
ansible -i ansible/inventory.ini webserver -m ping -vvv

# 4. Check passwordless sudo
ssh webserver@192.168.52.3 "sudo whoami"  # Must not prompt
```

### Passwordless Sudo Not Working

**Symptom:** Ansible prompts for password despite sudoers config

**Solution:**
```bash
# Verify sudoers file is correct
sudo cat /etc/sudoers.d/ansible-nopasswd

# If file doesn't exist or is wrong, recreate it:
sudo visudo -f /etc/sudoers.d/ansible-nopasswd

# Add this line (replace webserver with actual username):
# webserver ALL=(ALL) NOPASSWD: ALL

# Test it works (should not prompt for password):
sudo -l -U webserver
sudo whoami  # Must return "root"
```

### Backups Not Running

**Symptom:** `/backup/logs/` directory empty or no recent logs

**Solution:**
```bash
# 1. Check crontab is set
crontab -l | grep backup

# 2. View cron execution logs
grep CRON /var/log/syslog | tail -20

# 3. Run backup manually to see errors
/usr/bin/python3 /backup/scripts/backup_dbpostgre.py

# 4. Check backup directory permissions
ls -la /backup/
```

### PostgreSQL Won't Start

**Symptom:** Recovery playbook fails on dbserver

**Solution:**
```bash
# SSH to dbserver and check status
ssh dbserver@192.168.52.4

# View PostgreSQL logs
sudo tail -50 /var/log/postgresql/postgresql-*.log

# Try manual restart
sudo systemctl restart postgresql
sudo systemctl status postgresql

# If still fails, check disk space
df -h
```

### M/Monit Dashboard Not Accessible

**Symptom:** Cannot reach `http://192.168.52.5:8080`

**Solution:**
```bash
# 1. Verify M/Monit process is running
sudo systemctl status mmonit

# 2. Check if process is actually running
ps aux | grep mmonit

# 3. View M/Monit logs
sudo tail -50 /opt/mmonit/logs/mmonit.log

# 4. Restart the service
sudo systemctl restart mmonit
```

### Orchestrator Crashes or Hangs

**Symptom:** Orchestrator stops running or takes very long

**Solution:**
```bash
# 1. Check system resources
top -b -n 1 | head -20
free -h
df -h

# 2. Run orchestrator in foreground with debug output
python3 /backup/scripts/dr_orchestrator143.py -v

# 3. Check for hung SSH connections
ssh -o ConnectTimeout=5 webserver@192.168.52.3 "echo OK"

# 4. Review recent logs for errors
tail -100 /backup/logs/cron_dr.log
```

---

## 📞 Need More Help?

- **Setup issues?** Check the Prerequisites section or Troubleshooting above
- **Script errors?** Review logs in `/backup/logs/` directory
- **Want live examples?** See `docs/Final_Project_Report.pdf` for actual test runs
- **Code questions?** Read `docs/IMPLEMENTATION_GUIDE.md`

---

**Next Step:** Run `python3 /backup/scripts/dr_orchestrator143.py` to verify everything, then see [README.md](../README.md) for understanding the system architecture.
