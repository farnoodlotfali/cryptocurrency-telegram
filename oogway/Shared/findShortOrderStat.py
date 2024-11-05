# SHORT
from Shared.updateOHLC_FromAPI import updateOHLC_FromAPI
from Shared.helpers import addDaysToMilliTimeStamp
from Shared.dataIO import load_historic_tohlcv_json
from Shared.types import MarketName, Stat
from typing import Awaitable
from Shared.Constant import PostStatusValues


async def findShortOrderStat(stop_loss:float ,entry_price:list[float], symbolName:str, take_profit:list[float], start_timestamp: int, marketName:MarketName, max_day_wait:int = 10)-> Awaitable[Stat]:
    # max_day_wait helps avoid more waiting for a order status
    
    await updateOHLC_FromAPI(start_timestamp, symbolName, marketName, max_day_wait)
    LData = load_historic_tohlcv_json(symbolName=symbolName, marketName=marketName)

    tp_turn = 0
    tp = take_profit[tp_turn]
    tps = []

    entry_turn = 0
    entry = entry_price[entry_turn]
    entry_reached = []

    stop_loss_reached = None

    break_reason = None
    stop_timestamp = addDaysToMilliTimeStamp(start_timestamp, max_day_wait)

    # tohlcv
    # row[0] = timestamp
    # row[1] = open
    # row[2] = high
    # row[3] = low
    # row[4] = close
    # row[5] = volume
    for row in LData:
        # row[0] = timestamp
        if row[0] < start_timestamp:
            continue

        if max_day_wait and not bool(stop_loss_reached) and not bool(entry_reached) and not bool(tps):
            if row[0] > stop_timestamp:
                break_reason = PostStatusValues.WAIT_MANY_DAYS.value
                break

                                # row[2] = high
        if not entry_reached and float(row[2]) >= float(entry):
            entry_reached.append(row)

            if entry_turn < len(entry_price)-1:
                entry_turn += 1
                entry = entry_price[entry_turn]
            else:
                entry = float("inf")

            continue
                            # row[2] = high
        if entry_reached and float(row[2]) >= float(entry):
            entry_reached.append(row)

            if entry_turn < len(entry_price)-1:
                entry_turn += 1
                entry = entry_price[entry_turn]
            else:
                entry = float("inf")

            continue


        if bool(entry_reached):
                                                # row[2] = high
            if not bool(stop_loss_reached) and float(row[2]) >= float(stop_loss):
                
                stop_loss_reached = row
                break

                # row[3] = low
            if float(row[3]) <= float(tp):
                
                tps.append(row)
                tp_turn += 1

                if (tp_turn) == len(take_profit):
                    break
                tp = take_profit[tp_turn]
            
    
    return {"tps": tps, "entry_reached": entry_reached, "stop_loss_reached": stop_loss_reached, 'break_reason': break_reason} 

