# LONG

from Shared.updateOHLC_FromAPI import updateOHLC_FromAPI
from dotenv import dotenv_values
from bingx.api import BingxAPI
from PostAnalyzer.models import (
    Symbol,
)
from Shared.helpers import load_json

config = dotenv_values(".env")

API_KEY = config["API_KEY"]
SECRET_KEY = config["SECRET_KEY"]
historic_json_path = "./../historic-json"

bingx =  BingxAPI(API_KEY, SECRET_KEY, timestamp="local")

async def findLongOrderStat(stop_loss,entry_price,symbol:Symbol,take_profit,start_timestamp):
    print(stop_loss,entry_price,symbol,take_profit,start_timestamp)


    await updateOHLC_FromAPI(start_timestamp, symbol.name)
    LData = load_json(f"{historic_json_path}/{symbol.name}.json")

    tp_turn = 0
    tp = take_profit[tp_turn]
    tps = []

    entry_turn = 0
    entry = entry_price[entry_turn]
    entry_reached = []

    stop_loss_reached = None
        
    for row in LData:
        if row['time'] < start_timestamp:
            continue
        
        if not entry_reached and float(row['low']) <= float(entry):
            entry_reached.append(row)

            if entry_turn < len(entry_price)-1:
                entry_turn += 1
                entry = entry_price[entry_turn]
            else:
                entry = -float("inf")

            continue

        if entry_reached and float(row['low']) <= float(entry):
            entry_reached.append(row)

            if entry_turn < len(entry_price)-1:
                entry_turn += 1
                entry = entry_price[entry_turn]
            else:
                entry = -float("inf")

            continue

            
        if bool(entry_reached):
            if not bool(stop_loss_reached) and float(row['low']) <= float(stop_loss):
                
                stop_loss_reached = row
                keepOn = False
                break

            if float(row['high']) >= float(tp):
                
                tps.append(row)
                tp_turn += 1

                if (tp_turn) == len(take_profit):
                    keepOn = False
                    break
                tp = take_profit[tp_turn]
        
    
    return {"tps": tps, "entry_reached": entry_reached, "stop_loss_reached": stop_loss_reached}

