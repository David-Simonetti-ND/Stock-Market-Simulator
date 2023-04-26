import subprocess
import signal
import sys
import time
import random

procs = []
def handler(signum, frame):
    global procs
    subprocess.Popen(["condor_rm", "dsimone2"])
    for proc in procs:
        proc.kill()
    exit(0)
 
signal.signal(signal.SIGINT, handler)

condor_command = '''
executable     = /scratch365/dsimone2/scratch_conda/bin/python3 
arguments      = "/scratch365/dsimone2/distsys/Stock-Market-Simulator/src/random_player.py {project_name} {username}" 
request_cpus   = 1
request_memory = 2048
request_disk   = 4096


log     = client_log.{username}.log
queue 1
'''

names = []
with open("../names.txt", "r") as f:
    names = f.read().split("\n")

chosen_names = random.sample(names, int(sys.argv[2]))
log_files = []

for i in range(int(sys.argv[2])):
    with open(f"client{i}.txt", "w") as f:
        f.write(condor_command.format(project_name = sys.argv[1], username = chosen_names[i]))
    with open(f"client_log.{chosen_names[i]}.log", "w") as f:
        pass
    log_files.append(open(f"client_log.{chosen_names[i]}.log", "r"))
    subprocess.Popen(["condor_submit", f"client{i}.txt"])

while True:
    for i in range(len(log_files)):
        log = log_files[i]
        updates = log.read()
        if "aborted" in updates or "terminated" in updates:
            subprocess.Popen(["condor_submit", f"client{i}.txt"])
    time.sleep(1)