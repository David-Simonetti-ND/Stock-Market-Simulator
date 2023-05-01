# File: test_lft_reporter.py
# Author: John Lee (jlee88@nd.edu)

# Description: Reports Latencies for a LFT client.
# usage:
#   python test_lft_reporter.py <proj_name> <client_name>

from StockMarketEndpoint import *
import sys
import time

if __name__ == '__main__':
    
    # init stock market endpoint
    sm = StockMarketEndpoint(name=sys.argv[1], username=sys.argv[2], password=sys.argv[2])
    sm.register(registered_ok=True)
    
    while True:
    
        
        time.sleep(1)
        # measure buy operations
        start = time.time_ns()
        sm.buy('TSLA', 10)
        end = time.time_ns()
        print( end - start)
        # sell
        sm.sell('TSLA', 10)

            
        