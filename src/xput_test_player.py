from StockMarketEndpoint import *
import sys
import signal


def print_result(_, __):
    print(diff)
    exit(0)

if __name__ == '__main__':
    # init stock market endpoint
    sm = StockMarketEndpoint(name=sys.argv[1], username=sys.argv[2], password=sys.argv[2])
    
    sm.register()
    
    signal.signal(signal.SIGINT, print_result)
    
    prev = None
    diff = None
    while True:
        data = sm.get_stock_update()
        # still None
        if len(data) == 0:
            continue

        if prev is None:
            prev = data
        elif prev['time'] != data['time']:
            diff = (data['time'] - prev['time'])/1e9
            prev = data