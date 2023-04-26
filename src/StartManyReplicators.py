import subprocess
import sys
import os
import signal
import time

procs = []
def handler(signum, frame):
    for proc in procs:
        proc.kill()
    exit(0)

signal.signal(signal.SIGINT, handler)

try:
    os.mkdir("replicator_data")
except Exception:
    pass
try:
    os.chdir("replicator_data")
except Exception:
    exit(1)

for i in range(int(sys.argv[2])):
    try:
        os.mkdir(str(i))
    except Exception:
        pass
    os.chdir(str(i))
    procs.append(subprocess.Popen(["python3", "../../Replicator.py", sys.argv[1], f"{i}"]))
    os.chdir("..")

while True:
    time.sleep(1)
