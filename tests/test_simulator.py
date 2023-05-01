# File: test_simulator.py
# Author: John Lee (jlee88@nd.edu) 

# Description: Test script to test many clients connecting to the simulator only
# usage 
#   python test_simulator.py <proj_name> <num_clients>

import subprocess
from pathlib import Path
import sys
import signal

runs = []


def kill_runs(_, __):
    """Kill children"""
    for r in runs:
        r.send_signal(signal.SIGINT)
    exit(0)
        
def run_multiple_users(num_users, proj_name):
    global runs
    for i in range(num_users):
        # if i % 10 == 0:
        #     time.sleep(5)
        runs.append(subprocess.Popen(["python", "test_inactive_player.py", proj_name, 'user' + str(i)],
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        )
    
    signal.signal(signal.SIGINT, kill_runs)
    
    while True:
        pass


if __name__ == '__main__':
    run_multiple_users(int(sys.argv[2]), sys.argv[1])