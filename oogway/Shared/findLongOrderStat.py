# LONG
from Shared.updateOHLC_FromAPI import updateOHLC_FromAPI
from PostAnalyzer.models import (
    Symbol,
)
from Shared.helpers import load_historic_tohlcv_json


async def findLongOrderStat(stop_loss: float, entry_price: list[float], symbol:Symbol, take_profit: list[float],start_timestamp: int):
    print(stop_loss,entry_price,symbol,take_profit,start_timestamp)


    await updateOHLC_FromAPI(start_timestamp, symbol.name)
    LData = load_historic_tohlcv_json(symbol.name)

    tp_turn = 0
    tp = take_profit[tp_turn]
    tps = []

    entry_turn = 0
    entry = entry_price[entry_turn]
    entry_reached = []

    stop_loss_reached = None


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
                                    # row[3] = low
        if not entry_reached and float(row[3]) <= float(entry):
            entry_reached.append(row)

            if entry_turn < len(entry_price)-1:
                entry_turn += 1
                entry = entry_price[entry_turn]
            else:
                entry = -float("inf")

            continue
                                # row[3] = low
        if entry_reached and float(row[3]) <= float(entry):
            entry_reached.append(row)

            if entry_turn < len(entry_price)-1:
                entry_turn += 1
                entry = entry_price[entry_turn]
            else:
                entry = -float("inf")

            continue

            
        if bool(entry_reached):
                                                # row[3] = low
            if not bool(stop_loss_reached) and float(row[3]) <= float(stop_loss):
                stop_loss_reached = row
                break

                # row[2] = high
            if float(row[2]) >= float(tp):
                tps.append(row)
                tp_turn += 1

                if (tp_turn) == len(take_profit):
                    break
                tp = take_profit[tp_turn]
        
    
    return {"tps": tps, "entry_reached": entry_reached, "stop_loss_reached": stop_loss_reached}

