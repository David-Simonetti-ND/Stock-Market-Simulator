import sys, time

from StockMarketEndpoint import *

def main():
    if len(sys.argv) != 3:
        print("Error: please only enter two arguments which is the project name and your username")
        exit(1)

    # connect to broker & simulator
    sm = StockMarketEndpoint(name=sys.argv[1],
                             username=sys.argv[2],
                             password=sys.argv[2])
    
    while True:
        print(sm.get_stock_update())
        time.sleep(.1)
    # Authenticate self
    resp = sm.register()
    # just skip b/c it means this person already connected before
    if resp['Success'] == False:
        pass
    
    # random policy

    for i in range(5):
        print(sm.receive_latest_stock_update())
        response = sm.buy("TSLA", 10)
        print(response['Value'])
        time.sleep(1)
        response = sm.sell("TSLA", 10)
        print(response['Value'])
        
    print(sm.get_leaderboard())
    '''
    ht.connect_to_broker(sys.argv[1])
    print(f"{'Description of expected output':60} | status of response | response/error from server")
    response = ht.buy("TSL", 10)
    print(f"{'Buying 10 of TSL':60} |", response["Result"], "  |", response["Value"])
    response = ht.buy("BKF", 10)
    print(f"{'Buying 10 of BKF':60} |", response["Result"], "  |", response["Value"])
    response = ht.sell("NLE", 5)
    print(f"{'Selling 10 of NLE':60} |", response["Result"], "  |", response["Value"])
    response = ht.get_price("PER")
    print(f"{'Getting price of PER':60} |", response["Result"], "  |", response["Value"])
    ht.close_connection()
    '''

if __name__ == "__main__":
    main()