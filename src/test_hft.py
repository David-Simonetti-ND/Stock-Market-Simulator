from StockMarketEndpoint import *
import sys
import signal
import time

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
        
        