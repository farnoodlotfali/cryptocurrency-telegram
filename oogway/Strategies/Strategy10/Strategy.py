

from Shared.helpers import print_colored, load_historic_tohlcv_json
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


money_management = [
    # {     
    #     'id': 1,
    #     'start_date': "",
    #     'end_date': "",
    #     'money_used': "",
    #     'money_back': "",
    # }
]



def calStoploss(entry:float, leverage:int, isShort:bool, max_percent_stoploss:float):
    return entry*(1+(max_percent_stoploss/(100*leverage*(1 if isShort else -1)))) 


def updateMoneyManagement(id:int, end_date:int, money_back: float):
    for item in money_management:
        if item['id'] == id:
            item['end_date'] = end_date
            item['money_back'] = money_back
            break


def checkFreeMoneyManagement(start_date:int):
    free_money = 0
    for item in money_management:
        if start_date > item['end_date']:
           free_money += item['money_back'] + item['money_used']
           money_management.remove(item)

    return free_money

missed_orders = []

#strategy_10
async def backtest_with_money_strategy_10(predicts: list[Predict], my_money:float, close_tp:int=0, showPrint: bool= False, positionSize: float= 100, max_percent_stoploss: float=5):

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


        start_timestamp = int(pr.date.timestamp() * 1000)
        my_money += checkFreeMoneyManagement(start_timestamp)
        print(pr.symbol.name, my_money)
        if my_money < positionSize:
            print(pr.symbol.name, 'missed\n')
            # print_colored(pr.symbol.name + 'missed', 'red')

            missed_orders.append(model_to_dict(pr))
            continue


        entry_price = await sync_to_async(
            lambda: list(EntryTarget.objects.filter(post=pr.post).order_by('index'))
        )()

        take_profit = await sync_to_async(
            lambda: list(TakeProfitTarget.objects.filter(post=pr.post).order_by('index'))
        )()


        LData = load_historic_tohlcv_json(pr.symbol.name)
        isSHORT = pr.position.name == "SHORT"

        tp_turn = 0
        tp = take_profit[tp_turn].value
        tps = []

        new_entry = entry_price[0].value
        wait_for_entry = True
        entry_reached = []

        stop_loss_reached = None
        
        profit = 0
       
        stop_loss_profit = round(((pr.stopLoss/new_entry)-1)*pr.leverage * (-1 if isSHORT else 1), 5) 
        stop_loss = pr.stopLoss

        
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
                    my_money -= positionSize
                    money_management.append({
                        'id': pr.id,
                        'start_date': row[0],
                        'end_date': "",
                        'money_used': positionSize,
                        'money_back': "",
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
                        updateMoneyManagement(id=pr.id, end_date=row[0], money_back=profit)
                        
                        # 
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
                        updateMoneyManagement(id=pr.id, end_date=row[0], money_back=profit)
                        tp_turn += 1

                        if (tp_turn) == len(take_profit) or close_tp < len(tps):
                            #
                            break
                        tp = take_profit[tp_turn].value
                        stop_loss = round(((stop_loss_profit*new_entry)/pr.leverage)+new_entry, 5) 

        else:
            for row in LData:
                if row[0] < start_timestamp:
                    continue

                if wait_for_entry and float(row[2]) >= new_entry:
                    entry_reached.append({
                        'value': new_entry,
                        'tohlcv': row
                    })
                    my_money -= positionSize
                    money_management.append({
                        'id': pr.id,
                        'start_date': row[0],
                        'end_date': "",
                        'money_used': positionSize,
                        'money_back': "",
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
                        updateMoneyManagement(id=pr.id, end_date=row[0], money_back=profit)
                        #
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
                        updateMoneyManagement(id=pr.id, end_date=row[0], money_back=profit)
                        tp_turn += 1

                        if (tp_turn) == len(take_profit) or close_tp < len(tps):
                            #
                            break
                        tp = take_profit[tp_turn].value
                        stop_loss = round((((stop_loss_profit*new_entry)/pr.leverage) * -1)+new_entry, 5) 

        history = historyController(history=history, curr_money=my_money, entry_targets=entry_reached, predict=pr, profit=profit, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)

        if profit < 0:
            total_loss += profit
        else:
            total_profit += profit
        stat = {"tps": tps, "entry_reached": entry_reached, "stop_loss_reached": stop_loss_reached}
        # print(stat)
        print(profit)
        print('\n\n')

    for item in money_management:
        my_money += item['money_back'] + item['money_used']
     



    print_colored(f"initial money: {initial_my_money}", "gold")
    print_colored(f"total_opening_orders: {total_opening_orders}", "#1da44f")
    print_colored(f"total_loss: {total_loss}", "pink")
    print_colored(f"total_profit: {total_profit}", "green")
    print_colored(f"gross: {total_profit+total_loss}", "deeppink")
    print_colored(f"total_pending: {total_pending}", "grey")
    print_colored(f"my free money: {my_money}", "orange")
    print_colored(f"my total money: {my_money+total_pending}", "#d16984")
    print_colored(f"profit_count: {profit_count}, loss_count: {loss_count}, pending_count: {pending_count}", "#a1309d")
    # print(missed_orders)
    print(money_management)

    return history


