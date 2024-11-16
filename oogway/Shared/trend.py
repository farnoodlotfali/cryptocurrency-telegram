import pandas as pd
import numpy as np
from Shared.Constant import TrendValues, MarketValues
from Shared.helpers import  zero_hours_minutes_seconds
from Shared.dataIO import load_historic_tohlcv_json
from Shared.updateOHLC_FromAPI import updateOHLC_FromAPI
from bisect import bisect_left

def determine_trend(data:list[int], period:int=50) -> TrendValues:

    # tohlcv
    # df[0] = timestamp
    # df[1] = open
    # df[2] = high
    # df[3] = low
    # df[4] = close
    # df[5] = volume

    df = pd.DataFrame(data)

    if len(df) < period:
        raise ValueError("Not enough data points to calculate the moving average for the given period.")

    # Calculate the moving average
    df['MA'] = df[4].rolling(window=period).mean()

    # Calculate the slope (using linear regression on the last 'period' points)
    df['slope'] = np.polyfit(range(period), df[4].tail(period), 1)[0]

    # Determine the trend
    if df['slope'].iloc[-1] > 0 and df[4].iloc[-1] > df['MA'].iloc[-1]:
        return TrendValues.UPTREND.value
    elif df['slope'].iloc[-1] < 0 and df[4].iloc[-1] < df['MA'].iloc[-1]:
        return TrendValues.DOWNTREND.value
    else:
        return TrendValues.SIDEWAYS.value



async def check_trend_in_one_week_BTC(start_timestamp:int, period:int=50)-> TrendValues: 
    symbolName='BTC/USDT:USDT'
    marketName=MarketValues.FUTURES.value

    zero_start_timestamp = zero_hours_minutes_seconds(start_timestamp)

    LData = load_historic_tohlcv_json(symbolName=symbolName, marketName=marketName)

    timestamps = [row[0] for row in LData]

    li: list[int] = [(86_400_000 * (-x)) + zero_start_timestamp for x in range(1,8)]
    li.reverse()

    # Check each target timestamp in the list
    for item in li:
        index = bisect_left(timestamps, item)
        
        # Check if the item exists at the found index
        if index == len(timestamps) or timestamps[index] != item:
            await updateOHLC_FromAPI(start_timestamp, symbolName, marketName)
            LData = load_historic_tohlcv_json(symbolName=symbolName, marketName=marketName)
            break


    one_week_before_start_timestamp = li[0]

    one_week_data = []

    # tohlcv
    # row[0] = timestamp
    # row[1] = open
    # row[2] = high
    # row[3] = low
    # row[4] = close
    # row[5] = volume
    for row in LData:
        # row[0] = timestamp
        if row[0] < one_week_before_start_timestamp:
            continue
        if row[0] > zero_start_timestamp:
            break
        one_week_data.append(row)
   

    return determine_trend(one_week_data, period)