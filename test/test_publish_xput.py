import subprocess

NUM_CLIENTS = 5


procs = []
for i in range(NUM_CLIENTS):
    procs.append(subprocess.Popen(["python3", "random_player.py", "stock"]))

for i in range(NUM_CLIENTS):
    procs[i].wait()
