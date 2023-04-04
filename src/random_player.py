import sys, time

from StockMarketEndpoint import *

def main():
    if len(sys.argv) != 3:
        print("Error: please only enter two arguments which is the project name and your username")
        exit(1)

    sm = StockMarketEndpoint(sys.argv[1], sys.argv[2])
    sm.connect_to_broker()
    for i in range(5):
        print(sm.receive_latest_stock_update())
        response = sm.buy("TSLA", 10)
        print(f"{'Buying 10 of TSL':60} |", response["Result"], "  |", response["Value"])
        time.sleep(1)
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