import subprocess
import signal
import sys
import time
import random

procs = []
# clean up all clients on control-c
def handler(signum, frame):
    for proc in procs:
        proc.kill()
    exit(0)
 
def main():
    if len(sys.argv) != 4:
        print("Error: please enter project name, number of clients to start, and the path to the client program to start")
        exit(1)
    try:
        num_clients = int(sys.argv[2])
    except Exception:
        print("Error: the number of clients must be an integer")
        exit(1)

    # set up SIGINT handler to cleanup children
    signal.signal(signal.SIGINT, handler)

    # read in names file
    names = []
    with open("names.txt", "r") as f:
        names = f.read().split("\n")

    # randomly select some names from the pile
    chosen_names = random.sample(names, int(sys.argv[2]))

    # start n clients with a random name
    for i in range(num_clients):
        procs.append(subprocess.Popen(["python3", sys.argv[3], sys.argv[1], chosen_names[i]]))

    while True:
        # wait around for control-c to cleanup all children
        time.sleep(1)

if __name__ == "__main__":
    main()