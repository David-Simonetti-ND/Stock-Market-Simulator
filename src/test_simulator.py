# Test script to test multiple users collection

import subprocess
from pathlib import Path
import sys
import time
import signal

runs = []


def kill_runs(_, __):
    for r in runs:
        r.send_signal(signal.SIGINT)
    exit(0)
        
def run_multiple_users(num_users, proj_name):
    global runs
    for i in range(num_users):
        if i % 10 == 0:
            time.sleep(5)
        runs.append(subprocess.Popen(["python", "test_xput_player.py", proj_name, 'user' + str(i)],
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE)
        )
    
    signal.signal(signal.SIGINT, kill_runs)
    
    while True:
        pass
    # time.sleep(3)
    # intervals = []
    # users = []
    # for r in runs:
    #     stdout, stderr = r.communicate()
    #     stdout = stdout.decode("utf-8")
    #     # print(stdout, stderr)
    #     user, interval = stdout.rstrip().split(' ')
    #     intervals.append(float(interval))
    #     users.append(user)
        
        
    # print(users)
    # print(sum(intervals) / len(intervals))
    # print(max(intervals) - min(intervals))
    # print(max(intervals), min(intervals))


if __name__ == '__main__':
    run_multiple_users(int(sys.argv[2]), sys.argv[1])