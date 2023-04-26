import sys, time
import random

from StockMarketEndpoint import *
from StockMarketLib import VALID_TICKERS

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

    
    # random policy
    c = 0
    while True:
        time.sleep(1)
        
        action = random.choice(["buy", 'sell'])
        tkr = random.choice(VALID_TICKERS)
        amt = random.randint(1, 15)
        if action == 'buy':
            print(sm.buy(tkr, amt)['Value'])

        elif action == 'sell':
            print(sm.sell(tkr, amt)['Value'])
        
        if c % 10 == 0:
            print(sm.get_balance())
        if c % 60 == 0:
            print(sm.get_leaderboard())
            
        c+=1    
if __name__ == "__main__":
    main()