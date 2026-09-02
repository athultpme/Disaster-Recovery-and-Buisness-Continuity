#!/usr/bin/env python3
import subprocess
import os
os.environ['PGHOST'] = '192.168.52.4'
os.environ['PGPORT'] = '5432'
# Or subprocess: ['psql', '-h', '192.168.52.4', '-p', '5432', ...

subprocess.run("gunzip -c /backup/database/postgres_backup_latest.gz | psql healthcare_db", shell=True)
print(" Restore complete")
