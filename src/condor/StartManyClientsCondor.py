# File: StartManyClientsCondor.py
# Author: David Simonneti (dsimone2@nd.edu)
# 
# Description: Script to start multiple clients from HTCondor.

import subprocess
import signal
import sys
import time
import random
import os

procs = []
def handler(signum, frame):
    """Cleanup function for condor"""
    global procs
    # remove all condor jobs
    subprocess.Popen(["condor_rm", os.environ.get('USER')])
    # kill all child processes
    for proc in procs:
        proc.kill()
    exit(0)
 
def main():
    if len(sys.argv) != 4:
        print("Error: please enter project name, number of clients to start, and the path to the client program to run")
        exit(1)
    try:
        num_clients = int(sys.argv[2])
    except Exception:
        print("Error: the number of clients must be an integer")
        exit(1)

    signal.signal(signal.SIGINT, handler)

    # the condor command to be written out into a submit file to start a single client job
    # to change the client program to be run, change test_random_player.py to whatever is desired
    condor_command = '''
    executable     = /scratch365/{user}/stock_conda/bin/python3 
    arguments      = "{client_path} {project_name} {username}" 
    request_cpus   = 1
    request_memory = 2048
    request_disk   = 4096


    log     = client_log.{username}.log
    queue 1
    '''

    # read in random names file
    names = []
    with open("../data/names.txt", "r") as f:
        names = f.read().split("\n")

    # chose a random sample of them to use
    chosen_names = random.sample(names, num_clients)
    # keep track of log files for the clients
    log_files = []

    for i in range(num_clients):
        # write the submit file
        with open(f"client{i}.txt", "w") as f:
            f.write(condor_command.format(project_name = sys.argv[1], username = chosen_names[i], user=os.environ.get('USER'), client_path=sys.argv[3]))
        # create the log file
        with open(f"client_log.{chosen_names[i]}.log", "w") as f:
            pass
        # and add it to be kept track of
        log_files.append(open(f"client_log.{chosen_names[i]}.log", "r"))
        # submit the condor job for this client
        subprocess.Popen(["condor_submit", f"client{i}.txt"])

    while True:
        # watch over all started job's log files
        for i in range(len(log_files)):
            log = log_files[i]
            updates = log.read()
            # if the job died unexpectedly, just restart it
            if "aborted" in updates or "terminated" in updates:
                subprocess.Popen(["condor_submit", f"client{i}.txt"])
        # continue until control-c is received
        time.sleep(1)

if __name__ == "__main__":
    main()