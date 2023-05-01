# File: test_hft.py
# Author: John Lee (jlee88@nd.edu)

# Description: Generates a simple client that just sends buy/sell requests as fast as possible. 
# usage:
#   python test_hft.py <proj_name> <client_name>

from StockMarketEndpoint import *
import sys

if __name__ == '__main__':
    
    # init stock market endpoint
    sm = StockMarketEndpoint(name=sys.argv[1], username=sys.argv[2], password=sys.argv[2])
    sm.register(registered_ok=True)
    
    # signal.signal(signal.SIGINT, print_result)
    
    while True:
        # measure buy operations
        sm.buy('TSLA', 10)
        # sell
        sm.sell('TSLA', 10)
        
        