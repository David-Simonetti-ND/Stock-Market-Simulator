# Test script to test multiple users collection

import subprocess
from pathlib import Path
import sys
import time
import signal



def run_multiple_users(num_users, proj_name):

    runs = [subprocess.Popen(["python", "test_xput_player.py", proj_name, 'user' + str(i)],
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
            for i in range(num_users)]
    
    # sleep for a bit to stabilize
    time.sleep(10)
    for r in runs:
        r.send_signal(signal.SIGINT)
    
    time.sleep(3)
    intervals = []
    users = []
    for r in runs:
        stdout, stderr = r.communicate()
        stdout = stdout.decode("utf-8")
        # print(stdout, stderr)
        user, interval = stdout.rstrip().split(' ')
        intervals.append(float(interval))
        users.append(user)
        
        
    print(users)
    print(sum(intervals) / len(intervals))


if __name__ == '__main__':
    run_multiple_users(int(sys.argv[2]), sys.argv[1])