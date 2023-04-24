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

condor_command = '''
executable     = /scratch365/dsimone2/scratch_conda/bin/python3 
arguments      = "/scratch365/dsimone2/distsys/Stock-Market-Simulator/src/random_player.py {project_name} {username}" 
request_cpus   = 1
request_memory = 2048
request_disk   = 4096

queue 1
'''

names = []
with open("../names.txt", "r") as f:
    names = f.read().split("\n")

for i in range(int(sys.argv[2])):
    with open(f"client{i}.txt", "w") as f:
        f.write(condor_command.format(project_name = sys.argv[1], username = random.choice(names)))
    subprocess.Popen(["condor_submit", f"client{i}.txt"])

while True:
    time.sleep(1)
    if False:
        #for i in range(NUM_CLIENTS):
        procs[i].wait()
        i, l, q, r = procs[i].stdout.read().decode("utf-8").split("|")
        insert.append(float(i))
        lookup.append(float(l))
        query.append(float(q))
        remove.append(float(r))

        ins_avg = sum(insert) / NUM_CLIENTS
        look_avg = sum(lookup) / NUM_CLIENTS
        query_avg = sum(query) / NUM_CLIENTS
        rm_avg = sum(remove) / NUM_CLIENTS

 
    
        print(f"{NUM_CLIENTS} clients")
        print("-"*156)
        print(f"|{'Throughput(op/sec)':^30}|{'Insert':^30}|{'Lookup':^30}|{'Query':^30}|{'Remvove':^30}|")
        print("-"*156)
        for i in range(NUM_CLIENTS):
            print(f'''|{f'Worker {i}':^30}|{f'{insert[i]}':^30}|{f'{(lookup[i])}':^30}|{f'{query[i]}':^30}|{f'{remove[i]}':^30}|''')
            print("-"*156)
        print(f'''|{'Average Throughput(op/sec)':^30}|{f'{ins_avg}':^30}|{f'{(look_avg)}':^30}|{f'{query_avg}':^30}|{f'{rm_avg}':^30}|''')
        print("-"*156)
        print(f'''|{'Total Throughput(op/sec)':^30}|{f'{ins_avg * NUM_CLIENTS}':^30}|{f'{(look_avg * NUM_CLIENTS)}':^30}|{f'{query_avg * NUM_CLIENTS}':^30}|{f'{rm_avg * NUM_CLIENTS}':^30}|''')
        total_thu.append([ins_avg * NUM_CLIENTS, look_avg * NUM_CLIENTS, query_avg * NUM_CLIENTS, rm_avg * NUM_CLIENTS])
        print("-"*156)
        print("")
        print("-"*156)
        for i in range(len(total_thu)):
            ins_avg, look_avg ,query_avg, rm_avg = total_thu[i]
            print(f'''|{f'{i + 1} clients':^16}|{f'{ins_avg}':^30}|{f'{(look_avg)}':^30}|{f'{query_avg}':^30}|{f'{rm_avg}':^30}|''')
            print("-"*156)