import subprocess
import signal
import sys
import time
import random

procs = []
def handler(signum, frame):
    global procs
    for proc in procs:
        proc.kill()
    exit(0)
 
signal.signal(signal.SIGINT, handler)

names = []
with open("names.txt", "r") as f:
    names = f.read().split("\n")

chosen_names = random.sample(names, int(sys.argv[2]))

for i in range(int(sys.argv[2])):
    procs.append(subprocess.Popen(["python3", sys.argv[3], sys.argv[1], chosen_names]))

while True:
    time.sleep(1)
