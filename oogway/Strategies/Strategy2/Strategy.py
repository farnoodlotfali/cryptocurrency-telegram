

from Shared.helpers import print_colored
from Shared.dataIO import load_historic_tohlcv_json
from Shared.Constant import PostStatusValues
from Shared.findRiskToReward import findRiskToReward
from typing import Optional
from asgiref.sync import sync_to_async
from PostAnalyzer.models import (
    Predict,
    TakeProfitTarget,
    EntryTarget
)
from django.forms.models import model_to_dict

# ****************************************************************************************************************************

def calProfit(positionSize: float, profit: float)-> float:
    return positionSize*(profit/100)

def historyController(history: list, predict: Predict, curr_money:float, profit:float, stopLoss:float, take_profit_targets: list, entry_targets: list, stopLoss_time:list):
    model = model_to_dict(predict)
    model['symbol'] = predict.symbol.name
    model['market'] = predict.market.name
    model['position'] = predict.position.name

    model['current_money'] = curr_money
    model['profit'] = profit
    model['stopLoss'] = stopLoss
    model['stopLoss_time'] = stopLoss_time

    model['tps'] = take_profit_targets
    model['ens'] = entry_targets

    

    history.append(model)

    return history



def calStoploss(entry:float, leverage:int, isShort:bool, max_percent_stoploss:float):
    return entry*(1+(max_percent_stoploss/(100*leverage*(1 if isShort else -1)))) 

#strategy_2
async def backtest_with_money_strategy_2(predicts: list[Predict], my_money:float, close_tp:int=0, showPrint: bool= False, positionSize: float= 100, max_percent_stoploss: float=5):

    if not (0.5 <= max_percent_stoploss <= 100):
        raise ValueError(f"max_percent_stoploss should be between 0.5 and 100, but got {max_percent_stoploss}")
    

    total_loss = 0
    loss_count = 0
    total_profit = 0
    profit_count = 0
    total_pending = 0
    pending_count = 0
    initial_my_money = my_money
    total_opening_orders = 0

    history = []
  

    for i, pr in enumerate(predicts):

        if pr.status.name in [PostStatusValues.CANCELED.value, PostStatusValues.ERROR.value]:
            continue

        entry_price = await sync_to_async(
            lambda: list(EntryTarget.objects.filter(post=pr.post).order_by('index'))
        )()

        take_profit = await sync_to_async(
            lambda: list(TakeProfitTarget.objects.filter(post=pr.post).order_by('index'))
        )()


        LData = load_historic_tohlcv_json(pr.symbol.name, pr.market.name)
        isSHORT = pr.position.name == "SHORT"

        tp_turn = 0
        tp = take_profit[tp_turn].value
        tps = []

        new_entry = entry_price[0].value
        wait_for_entry = True
        entry_reached = []

        stop_loss_reached = None
        start_timestamp = int(pr.date.timestamp() * 1000)
        profit = 0
       
        stop_loss = calStoploss(new_entry, pr.leverage, isSHORT, max_percent_stoploss)
        
        # tohlcv
        # row[0] = timestamp
        # row[1] = open
        # row[2] = high
        # row[3] = low
        # row[4] = close
        # row[5] = volume
        if pr.position.name == "LONG":
            for row in LData:
                if row[0] < start_timestamp:
                    continue
                
                if wait_for_entry and float(row[3]) <= new_entry:
                    
                    entry_reached.append({
                        'value': new_entry,
                        'tohlcv': row
                    })

                    wait_for_entry = False
                    continue

                if bool(entry_reached) and not wait_for_entry:
                    if float(row[3]) <= stop_loss:
                        profit += round(((stop_loss/new_entry)-1)*100*pr.leverage * 1, 5) 

                        stop_loss_reached = {
                            'value': new_entry,
                            'tohlcv': row
                        }
                        history = historyController(history=history, curr_money=my_money, entry_targets=entry_reached, predict=pr, profit=profit, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)
                        break

                    if float(row[2]) >= tp: 
                        # wait_for_entry = True

                        profit_value = round(((tp/new_entry)-1)*100*pr.leverage * 1, 5)
                        profit += profit_value

                        new_entry = take_profit[tp_turn].value

                        tps.append({
                            'value': tp,
                            'tohlcv': row
                        })
                        tp_turn += 1

                        if (tp_turn) == len(take_profit) or close_tp < len(tps):
                            history = historyController(history=history, curr_money=my_money, entry_targets=entry_reached, predict=pr, profit=profit, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)
                            break
                        tp = take_profit[tp_turn].value
                        if tp_turn == 1:
                            stop_loss = entry_price[0].value
                        else:
                            stop_loss = take_profit[tp_turn-2].value
        else:
            for row in LData:
                if row[0] < start_timestamp:
                    continue

                if wait_for_entry and float(row[2]) >= new_entry:
                    entry_reached.append({
                        'value': new_entry,
                        'tohlcv': row
                    })

                    wait_for_entry = False

                    continue

                if bool(entry_reached) and not wait_for_entry:
                    if float(row[2]) >= stop_loss:
                        profit += round(((stop_loss/new_entry)-1)*100*pr.leverage * -1, 5)  
                        
                        stop_loss_reached = {
                            'value': new_entry,
                            'tohlcv': row
                        }
                        history = historyController(history=history, curr_money=my_money, entry_targets=entry_reached, predict=pr, profit=profit, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)

                        break

                    if float(row[3]) <= tp:
                        # wait_for_entry = True

                        profit_value = round(((tp/new_entry)-1)*100*pr.leverage * -1, 5)
                        profit += profit_value
                        
                        new_entry = take_profit[tp_turn].value

                        tps.append({
                            'value': tp,
                            'tohlcv': row
                        })
                        tp_turn += 1

                        if (tp_turn) == len(take_profit) or close_tp < len(tps):
                            history = historyController(history=history, curr_money=my_money, entry_targets=entry_reached, predict=pr, profit=profit, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)

                            break
                        tp = take_profit[tp_turn].value
                        if tp_turn == 1:
                            stop_loss = entry_price[0].value
                        else:
                            stop_loss = take_profit[tp_turn-2].value


        if profit < 0:
            total_loss += profit
        else:
            total_profit += profit
        stat = {"tps": tps, "entry_reached": entry_reached, "stop_loss_reached": stop_loss_reached}
        # print(stat)
     



    print_colored(f"initial money: {initial_my_money}", "gold")
    print_colored(f"total_opening_orders: {total_opening_orders}", "#1da44f")
    print_colored(f"total_loss: {total_loss}", "pink")
    print_colored(f"total_profit: {total_profit}", "green")
    print_colored(f"gross: {total_profit+total_loss}", "deeppink")
    print_colored(f"total_pending: {total_pending}", "grey")
    print_colored(f"my free money: {my_money}", "orange")
    print_colored(f"my total money: {my_money+total_pending}", "#d16984")
    print_colored(f"profit_count: {profit_count}, loss_count: {loss_count}, pending_count: {pending_count}", "#a1309d")

    return history


