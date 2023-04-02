from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime
from StockMarketLib import VALID_TICKERS
import pandas as pd

key = "PKQLQWISAMDP4032PHJR"
secret_key = "Gs1cISjv3MOKBA1F2ioDI3adwM5TLN7AodgaiJm8"

c = StockHistoricalDataClient(api_key=key, secret_key=secret_key)

# retrieve data since March 1, 2023
for ticker in VALID_TICKERS:
    rparams = StockBarsRequest(symbol_or_symbols=ticker,
                            timeframe=TimeFrame.Minute,
                            start=datetime.strptime("2023-03-01", '%Y-%m-%d'))
    bars = c.get_stock_bars(rparams).df

    bars = bars.fillna(method='ffill')

    # clean data
    pd.to_pickle(bars, f'data/{ticker}.pd')