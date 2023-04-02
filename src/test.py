from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

key = "PKQLQWISAMDP4032PHJR"
secret_key = "Gs1cISjv3MOKBA1F2ioDI3adwM5TLN7AodgaiJm8"

c = StockHistoricalDataClient(api_key=key, secret_key=secret_key)


rparams = StockBarsRequest(symbol_or_symbols=["TSLA", "MSFT"],
                        timeframe=TimeFrame.Min,
                        start=datetime.strptime("2022-07-01", '%Y-%m-%d'))
c.get_stock_bars()