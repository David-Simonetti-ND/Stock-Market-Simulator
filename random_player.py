import sys

from StockMarketClient import *

def main():
    if len(sys.argv) != 2:
        print("Error: please only enter one argument which is the project name")
        exit(1)

    ht = StockMarketClient()
    ht.connect_to_server(sys.argv[1])
    print(f"{'Description of expected output':60} | status of response | response/error from server")
    response = ht.buy("STOCK_A", 10)
    print(f"{'Buying 10 of STOCK_A':60} |", response["Result"], "  |", response["Value"])
    response = ht.buy("STOCK_C", 10)
    print(f"{'Buying 10 of STOCK_C':60} |", response["Result"], "  |", response["Value"])
    response = ht.sell("STOCK_A", 5)
    print(f"{'Selling 10 of STOCK_A':60} |", response["Result"], "  |", response["Value"])
    response = ht.get_price("STOCK_D")
    print(f"{'Getting price of STOCK_D':60} |", response["Result"], "  |", response["Value"])
    ht.close_connection()
    

if __name__ == "__main__":
    main()