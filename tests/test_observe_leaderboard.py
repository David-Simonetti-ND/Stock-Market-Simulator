# File: test_observe_leaderboard.py
# Author: John Lee (jlee88@nd.edu)

# Description: A client that only retrieves the leaderboard every minute.
# usage:
#   python test_observe_leaderboard.py <proj_name>

from StockMarketEndpoint import *
import sys
import time
import re
from collections import defaultdict

if __name__ == '__main__':
    
    # init stock market endpoint
    sm = StockMarketEndpoint(name=sys.argv[1], username="lb_obs", password="lb_obs")
    sm.register(registered_ok=True)
    
    file = "leaderboard.txt"
    
    net_worths = defaultdict(list)
    
    while True:
        time.sleep(60)
        lb = sm.get_leaderboard()
        
        # parse leaderboard
        for row in lb:
            m = re.search("(.*) | (.*)\n", row)
            if m is None:
                continue
            else:
                net_worths[m.group(1)].append(float(m.group(2)))
                
        # write output
        with open(file, 'a') as f:
            for user in sorted(net_worths.keys()):
                f.write(net_worths[user][-1], end = ' ')
            f.write('\n')
            
            
        
            
                
        