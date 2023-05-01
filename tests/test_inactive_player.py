# File: test_inactive_player.py
# Author: John Lee (jlee88@nd.edu) 

# Description: Creates 10 inactivate players.
# usage 
#   python test_simulator.py <proj_name> <client_name>

from StockMarketEndpoint import *
import sys
import time

if __name__ == '__main__':
    
    sm = []
    # init stock market endpoint
    for i in range(10):
        sm.append(StockMarketEndpoint(name=sys.argv[1], username=sys.argv[2], password=sys.argv[2]))
        sm[-1].register(registered_ok=True)
    
    while True:
        time.sleep(100)