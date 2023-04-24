from StockMarketEndpoint import *
import sys
import signal


def print_result(_, __):
    print(sm.username, diff_time)
    exit(0)

if __name__ == '__main__':
    # init stock market endpoint
    sm = StockMarketEndpoint(name=sys.argv[1], username=sys.argv[2], password=sys.argv[2])
    
    sm.register(registered_ok=True)
    
    # signal.signal(signal.SIGINT, print_result)
    
    prev = None
    prev_time = None
    diff_time = None
    while True:
        pass
        # data = sm.get_stock_update()
        # # still None
        # if len(data) == 0:
        #     continue

        # if prev is None:
        #     prev = data
        #     prev_time= time.time_ns()
        # elif prev['time'] != data['time']:
        #     tmp = time.time_ns()
        #     diff_time = (tmp - prev_time)/1e9
        #     prev = data
        #     prev_time = tmp