#!/bin/sh
cd /home/user/S-per-Lig-Fantasy-Manager/azur
setsid nohup python3 scene/render_queue.py > .cache/queue_run.txt 2>&1 < /dev/null &
