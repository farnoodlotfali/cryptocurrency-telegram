from bingx.api import BingxAPI
from dotenv import dotenv_values

import sys
project_path = '../../'  # Adjust this to your actual project path
sys.path.append(project_path)

from PostAnalyzer.Utility.utils import load_json, getNowTimestamp, print_colored
from Shared.saveOHLC_toJson import saveOHLC_toJson

config = dotenv_values(".env")

API_KEY = config["API_KEY"]
SECRET_KEY = config["SECRET_KEY"]

bingx =  BingxAPI(API_KEY, SECRET_KEY, timestamp="local")
historic_json_path = "./../historic-json"

async def updateOHLC_FromAPI(start_timestamp, symbolName):

    LData = load_json(f"{historic_json_path}/{symbolName}.json")

    keepOn = True
    time_interval = "1m" 
    # 60 * 24 = 1440 minutes in a day
    limit = 1440
    # 86400000 == milliseconds in a day
    milliSecInDay = 86_400_000    
    # 60_000 == milliseconds in a minute
    milliSecInMinute = 60_000

    allAPIdata = []

    # merge json data to api data
    if LData:
        print_colored("LData exists", "#f6cd28")

        first_item_time = LData[0]['time']
        last_item_time = LData[len(LData)-1]['time']

        # get older data
        if start_timestamp < ( first_item_time - milliSecInMinute):
            print_colored("get older data","#0ff")

            start_timestamp = start_timestamp - milliSecInMinute
            end_time = first_item_time
            next_day = start_timestamp + milliSecInDay

            while keepOn:
                
                res = bingx.get_kline_data(symbolName, time_interval, start_timestamp, next_day, limit)
                allAPIdata += list(reversed(res))

                start_timestamp = next_day
                next_day = start_timestamp + milliSecInDay

                if allAPIdata[len(allAPIdata)-1]['time'] > end_time:
                    keepOn = False
                    break
                if len(res) < limit:
                    keepOn = False
                    break


        # If the difference between the last item and the current time was more than one day, request to get new data
        if (getNowTimestamp() - last_item_time) > milliSecInDay:
            print_colored("get new data", "#00f")

            # api to get newer data
            keepOn = True
            start_timestamp = last_item_time - milliSecInMinute
            next_day = start_timestamp + milliSecInDay

            while keepOn:
                
                res = bingx.get_kline_data(symbolName, time_interval, last_item_time, next_day, limit)
                allAPIdata += list(reversed(res)) 

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
            res = bingx.get_kline_data(symbolName, time_interval, start_timestamp, next_day, limit)
            allAPIdata += list(reversed(res)) 

            start_timestamp = next_day
            next_day = start_timestamp + milliSecInDay
            
            if len(res) < limit:
                keepOn = False
                break

    if allAPIdata:
        print_colored("saveOHLC_toJson", "#ada")
        await saveOHLC_toJson(symbolName, historic_json_path, LData + allAPIdata)
