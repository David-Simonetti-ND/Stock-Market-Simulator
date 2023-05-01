import sys, time
import random
from collections import defaultdict

from StockMarketEndpoint import *
from StockMarketLib import VALID_TICKERS


def main():
    if len(sys.argv) != 3 and len(sys.argv) != 4:
        print("Error: please only enter two arguments which is the project name and your username")
        exit(1)
    
    raw_mode = False
    if len(sys.argv) == 4 and sys.argv[-1] == '-raw':
        raw_mode = True 
    
    # connect to broker & simulator
    sm = StockMarketEndpoint(name=sys.argv[1],
                             username=sys.argv[2],
                             password=sys.argv[2])
    # Authenticate self
    resp = sm.register(registered_ok=True)
    
    # wait for first data to come in.
    while sm.get_stock_update()['time'] == 0:
        pass
    
    while True:
        inp = input("> ")
        
        if inp == "menu":
            print("""Options:
                  menu
                  prices
                  buy
                  sell
                  balance
                  leaderboard
                  """)
        elif inp == 'prices':
            print(sm.get_stock_update())
        elif inp == "buy":
            ticker = input("Ticker: ")
            amt = int(input("Amount: "))
            resp = sm.buy(ticker, amt)
            if raw_mode:
                print(resp)
            else:
                print(resp['Value'])
        elif inp == "sell":
            ticker = input("Ticker: ")
            amt = int(input("Amount: "))
            resp = sm.sell(ticker, amt)
            if raw_mode:
                print(resp)
            else:
                print(resp['Value'])
        elif inp == 'balance':
            resp = sm.get_balance()
            if raw_mode:
                print(resp)
            else:
                print(resp['Str'])
                
        elif inp == 'leaderboard':
            resp = sm.get_leaderboard()
            print(resp)

if __name__ == "__main__":
    main()
