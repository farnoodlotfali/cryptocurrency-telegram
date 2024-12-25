
from typing import Awaitable
from Shared.Exchange import exchange
from Shared.Constant import  OrderType, EXCHANGE_LIMIT_OHLCV_DATA

async def updateEntryInMarketValue(entry_price:list[float, str], symbolName:str, start_timestamp:int)-> Awaitable[list[float, str]]:
    
    first_entry = entry_price[0]

    if first_entry == OrderType.MARKET.value:
        time_interval = "1m"
        limit = EXCHANGE_LIMIT_OHLCV_DATA
        # tohlcv
        # res[0][0] = timestamp
        # res[0][1] = open
        # res[0][2] = high
        # res[0][3] = low
        # res[0][4] = close
        # res[0][5] = volume
        res = exchange.fetch_ohlcv(symbol=symbolName, timeframe=time_interval, limit=limit, since=start_timestamp)
        # print(symbolName, time_interval, limit, start_timestamp, res)
        entry_price.remove(first_entry)
        entry_price.insert(0, float(res[0][3]))

    return entry_price
   

