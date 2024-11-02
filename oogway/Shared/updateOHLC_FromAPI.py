from Shared.helpers import getNowTimestamp, print_colored, addDaysToMilliTimeStamp
from Shared.dataIO import load_historic_tohlcv_json, save_historic_tohlcv_json
from Shared.Exchange import exchange
from Shared.types import MarketName
from typing import Optional


async def updateOHLC_FromAPI(start_timestamp:int, symbolName:str, marketName:MarketName, max_day_wait:Optional[int]):
    # max_day_wait helps avoid more waiting for a order status
   
    LData = load_historic_tohlcv_json(symbolName=symbolName, marketName=marketName)

    keepOn = True
    time_interval = "1m" 
    # 60 * 24 = 1440 minutes in a day
    limit = 1440
    # 86400000 == milliseconds in a day
    milliSecInDay = 86_400_000  

    # for better analyzing, we will decrease one minute form every times 
    # 60_000 == milliseconds in a minute
    milliSecInMinute = 60_000

    allAPIdata = []

    stop_timestamp = float('inf')
    if max_day_wait:
        stop_timestamp = addDaysToMilliTimeStamp(start_timestamp, max_day_wait)

    # tohlcv
    # LData[x][0] = timestamp
    # LData[x][1] = open
    # LData[x][2] = high
    # LData[x][3] = low
    # LData[x][4] = close
    # LData[x][5] = volume

    # merge json data to api data
    if LData:
        print_colored("LData exists", "#f6cd28")

        # get first item timestamp of LOADED tohlcv data
        first_item_time = LData[0][0]
        # get last item timestamp of LOADED tohlcv data
        last_item_time = LData[len(LData)-1][0]
       

        # get older data
        if start_timestamp < (first_item_time - milliSecInMinute):
            print_colored("get older data","#0ff")

            start_timestamp = start_timestamp - milliSecInMinute
            end_time = first_item_time
            next_day = start_timestamp + milliSecInDay

            while keepOn:
                res = exchange.fetch_ohlcv(symbol=symbolName, timeframe=time_interval, limit=limit, since=start_timestamp, params={
                    'until': next_day
                })
                allAPIdata += list(res)

                start_timestamp = next_day
                next_day = start_timestamp + milliSecInDay

                # if last item timestamp of API tohlcv data is bigger than end_time
                if allAPIdata[len(allAPIdata)-1][0] > end_time:
                    keepOn = False
                    break
                if len(res) < limit:
                    keepOn = False
                    break


        # If the difference between the last timestamp and the current time was more than one day, request to get new data
        if (getNowTimestamp() - last_item_time) > milliSecInDay:
            print_colored("get new data", "#00f")

            # api to get newer data
            keepOn = True
            start_timestamp = last_item_time - milliSecInMinute
            next_day = start_timestamp + milliSecInDay

            while keepOn:
                
                res = exchange.fetch_ohlcv(symbol=symbolName, timeframe=time_interval, limit=limit, since=start_timestamp, params={
                    'until': next_day
                })
                allAPIdata += list(res) 

                # avoid more waiting
                if stop_timestamp < next_day:
                    print_colored("stop_timestamp", "#ff0")
                    keepOn = False
                    break

                start_timestamp = next_day
                next_day = start_timestamp + milliSecInDay
                
                if len(res) < limit:
                    keepOn = False
                    break

    # json data is empty, so fill with api data until now
    else:
        print_colored("json is empty", "#c01")
        start_timestamp = start_timestamp - milliSecInMinute
        next_day = start_timestamp + milliSecInDay 
        while keepOn:
            res = exchange.fetch_ohlcv(symbol=symbolName, timeframe=time_interval, limit=limit, since=start_timestamp, params={
                'until': next_day
            })
            allAPIdata += list(res) 

            start_timestamp = next_day
            next_day = start_timestamp + milliSecInDay
            
            if len(res) < limit:
                keepOn = False
                break
                
    if allAPIdata:
        print_colored("saving historic tohlcv data to json", "#ada")
        save_historic_tohlcv_json(symbolName=symbolName, marketName=marketName, data=LData + allAPIdata )
