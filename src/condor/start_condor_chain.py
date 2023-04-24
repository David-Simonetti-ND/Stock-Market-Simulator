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

condor_command = '''
executable     = /scratch365/dsimone2/scratch_conda/bin/python3 
arguments      = "/scratch365/dsimone2/distsys/Stock-Market-Simulator/src/ChainReplicator.py {project_name} {chain_number}" 
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


signal.signal(signal.SIGINT, handler)

for i in range(int(sys.argv[2])):
    with open(f"table{i}.ckpt", "w") as f:
        f.write("0\n")
    with open(f"table{i}.txn", "w") as f:
        pass
    with open(f"log.{i}", "w") as f:
        pass
exit(1)
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