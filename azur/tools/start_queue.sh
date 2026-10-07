#!/bin/sh
# Starts the overnight renders detached: the view queue first, then the camera moves.
# Both skip finished outputs, so this is safe to run again after a restart. Does nothing if they already run.
cd /home/user/S-per-Lig-Fantasy-Manager/azur
if pgrep -f "python3 scene/render_(queue|moves).py" > /dev/null; then echo "renders already running"; exit 0; fi
setsid nohup sh -c 'python3 scene/render_queue.py > .cache/queue_run.txt 2>&1; python3 scene/render_moves.py > .cache/moves_run.txt 2>&1' < /dev/null > /dev/null 2>&1 &
echo "renders started"
