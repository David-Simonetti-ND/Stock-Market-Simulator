import subprocess
import sys
import os
import signal
import time

procs = []
# causes this process to kill all of its children when it receieves SIGINT
def handler(signum, frame):
    for proc in procs:
        proc.kill()
    exit(0)

def main():
    if len(sys.argv) != 3:
        print("Error: please enter project name and number of replicators to start")
        exit(1)
    try:
        num_replicators = int(sys.argv[2])
    except Exception:
        print("Error: the number of replicators must be an integer")
        exit(1)

    # set up signal handler
    signal.signal(signal.SIGINT, handler)

    # make directory for replicators to live in
    try:
        os.mkdir("replicator_data")
    except Exception:
        pass
    try:
        os.chdir("replicator_data")
    except Exception:
        print("Error in moving to correct directory")
        exit(1)

    for i in range(num_replicators):
        # make the directory for each individual replicator to live in
        try:
            os.mkdir(str(i))
        except Exception:
            pass
        os.chdir(str(i))
        # start the replicator process
        procs.append(subprocess.Popen(["python3", "../../Replicator.py", sys.argv[1], f"{i}"]))
        os.chdir("..")

    # wait around so that when control-c is pressed, all child replicators are culled by signal handler
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()