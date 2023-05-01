# File: GetData.py
# File Created: Sunday, 2nd April 2023 3:53:24 am
# Author: John Lee (jlee88@nd.edu)
# Last Modified: Monday, 1st May 2023 1:37:33 pm
# Modified By: John Lee (jlee88@nd.edu>)
# 
# Description: Script to retrieve Historical data, not relevant to distributed system. To use to update data, must pip install alpaca, and provide api/secret keys.

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
from StockMarketLib import VALID_TICKERS
import sys

# KEYS ARE passed in via cmd args
key = sys.argv[1]
secret_key = sys.argv[2]

c = StockHistoricalDataClient(api_key=key, secret_key=secret_key)

# retrieve data since March 1, 2023
for ticker in VALID_TICKERS:
    rparams = StockBarsRequest(symbol_or_symbols=ticker,
                            timeframe=TimeFrame.Minute,
                            start=datetime.strptime("2023-03-01", '%Y-%m-%d'))
    bars = c.get_stock_bars(rparams).df

    bars = bars.fillna(method='ffill')

    # clean data
    bars.to_csv(f'src/data/{ticker}.csv')