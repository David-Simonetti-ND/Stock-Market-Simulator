import subprocess
import shutil
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

#shutil.rmtree("chain")
#os.mkdir("chain")
os.chdir("chain")

for i in range(int(sys.argv[2])):
    try:
        os.mkdir(str(i))
    except Exception:
        pass
    os.chdir(str(i))
    procs.append(subprocess.Popen(["python3", "../../ChainReplicator.py", sys.argv[1], f"{i}"]))
    os.chdir("..")

while True:
    time.sleep(1)