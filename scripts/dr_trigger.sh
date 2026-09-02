#!/bin/bash

echo "DR triggered at $(date)" >> /backup/scripts/dr_trigger.log

# Fixed: was calling dr_orchestrator.py, which does not exist.
# The real script on disk is dr_orchestrator143.py.
# (Recommend renaming it to dr_orchestrator.py to drop the version
# suffix once you're happy with it, then updating this line back.)
python3 /backup/scripts/dr_orchestrator143.py
