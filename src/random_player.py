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
    resp = None
    while resp == None:
        resp = sm.register()
    
    # just skip b/c it means this person already connected before
    if resp['Success'] == False:
        pass
    
    # random policy
    c = 0
    while True:
        #time.sleep(1)
        
        action = random.choice(["buy", 'sell'])
        tkr = random.choice(VALID_TICKERS)
        amt = random.randint(1, 15)
        if action == 'buy':
            while True:
                resp = sm.buy(tkr, amt)
                if resp['Success'] != None and resp['Value'] != "User associated with Username does not exist.":
                    #print(resp['Value'], sm.username)
                    break
                else:
                    #print(resp, sm.username)
                    sm.register()

        elif action == 'sell':
            while True:
                resp = sm.sell(tkr, amt)
                if resp['Success'] != None and resp['Value'] != "User associated with Username does not exist.":
                    #print(resp['Value'], sm.username)
                    break
                else:
                    #print(resp, sm.username)
                    sm.register()
        
        if False:
            if c % 10 == 0:
                print(sm.get_balance(), sm.username)
            if c % 60 == 0:
                print(sm.get_leaderboard())
            
        c+=1    
if __name__ == "__main__":
    main()