import sys
sys.path.append('../src/')
import sys, time
import random
from collections import defaultdict

from StockMarketEndpoint import *
from StockMarketLib import VALID_TICKERS

def get_val(stock_returns):
    """ Gets probability of up/down and average return, computing expected value for each ticker"""
    up = 0
    up_count = 0
    down = 0
    down_count = 0
    # count prob and total value
    for r in stock_returns:
        if r < 0:
            down_count += 1
            down += r
        elif r > 0:
            up_count += 1
            up += r
    # average up and average down
    down /= down_count
    up /= up_count
    # prob up and down
    down_count /= len(stock_returns)
    up_count /= len(stock_returns)
    # expected value
    e_val = down * down_count + up * up_count
    return e_val              

def get_best_ticker(returns):
    """ Gets best ticker"""
    best_e_val = 0
    best_ticker = None
    for ticker in VALID_TICKERS:
        e_val = get_val(returns[ticker])
        if e_val > best_e_val:
            best_e_val = e_val
            best_ticker = ticker

    return best_ticker
        

def main():
    if len(sys.argv) != 3:
        print("Error: please only enter two arguments which is the project name and your username")
        exit(1)

    # connect to broker & simulator
    sm = StockMarketEndpoint(name=sys.argv[1],
                             username=sys.argv[2],
                             password=sys.argv[2])
    # Authenticate self
    resp = sm.register(registered_ok=True)
    
    # wait for first data to come in.
    while sm.get_stock_update()['time'] == 0:
        pass
    
    
    # Init variables

    # Init markov model
    # Based on previous data, guess the probability and return of data, to compute expected value over next 500 publishes
    # 600 publishes a minute
    # First 100 is used to guess which one has more increases
    first_up = sm.get_stock_update()
    publishes = 0
    prev_update = first_up
    returns = defaultdict(list)
    while True:
        update = sm.get_stock_update()
        
        # check that an update was actually made
        if prev_update['time'] != update['time']:
            
            
            # store returns
            if publishes < 100:
                for ticker in VALID_TICKERS:
                    returns[ticker].append(update[ticker] - prev_update[ticker])
            # send buy request
            elif publishes == 100:
                buy_ticker = get_best_ticker(returns)
                if buy_ticker is None:
                    # no value was good, reset
                    publishes = -1
                    returns = defaultdict(list)
                else:
                    # purchase as many stocks of buy_ticker as possible
                    cash = sm.get_balance()['Cash']
                    amt = cash // update[buy_ticker]
                    sm.buy(buy_ticker, amt)
            # sell and reset
            elif publishes == 600:
                sm.sell(buy_ticker, amt)
                publishes = -1
                returns = defaultdict(list)
                
            # update previous
            prev_update = update
            publishes += 1
    


if __name__ == '__main__':
    
    main()