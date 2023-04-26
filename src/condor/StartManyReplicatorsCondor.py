import subprocess
import shutil
import sys
import os
import signal
import time

procs = []
def handler(signum, frame):
    subprocess.Popen(["condor_rm", "dsimone2"])
    for proc in procs:
        proc.kill()
    exit(0)

condor_command = '''
executable     = /scratch365/dsimone2/scratch_conda/bin/python3 
arguments      = "/scratch365/dsimone2/distsys/Stock-Market-Simulator/src/Replicator.py {project_name} {chain_number}" 
should_transfer_files=yes
transfer_input_files = table{chain_number}.ckpt, table{chain_number}.txn, table.ckpt.shadow
request_cpus   = 1
request_memory = 2048
request_disk   = 4096

error   = output/err.{chain_number}
output  = output/out.{chain_number}
log     = log.{chain_number}
queue 1
'''

with open(f"table.ckpt.shadow", "w") as f:
    pass
signal.signal(signal.SIGINT, handler)

log_files = []
for i in range(int(sys.argv[2])):
    with open(f"table{i}.ckpt", "w") as f:
        f.write("0\n")
    with open(f"table{i}.txn", "w") as f:
        pass
    with open(f"log.{i}", "w") as f:
        pass
    with open(f"job{i}.txt", "w") as f:
        f.write(condor_command.format(project_name = sys.argv[1], chain_number = i))
    log_files.append(open(f"log.{i}", "r"))

for i in range(int(sys.argv[2])):
    subprocess.Popen(["condor_submit", f"job{i}.txt"])

while True:
    for i in range(len(log_files)):
        log = log_files[i]
        updates = log.read()
        if "aborted" in updates or "terminated" in updates:
            subprocess.Popen(["condor_submit", f"job{i}.txt"])
    time.sleep(1)