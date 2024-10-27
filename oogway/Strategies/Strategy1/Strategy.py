
from Shared.helpers import print_colored, compare_two_numbers
from Shared.Constant import PostStatusValues
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

def historyController(history: list, predict: Predict, curr_money:float, profit:float, take_profit_target: Optional[TakeProfitTarget]= None, entry_target: Optional[EntryTarget]= None):
    model = model_to_dict(predict)
    model['symbol'] = predict.symbol.name
    model['market'] = predict.market.name
    model['position'] = predict.position.name

    model['current_money'] = curr_money
    model['profit'] = profit

    model['tp_value'] = take_profit_target.value if take_profit_target else None
    model['tp_index'] = take_profit_target.index if take_profit_target else None
    model['tp_date'] = take_profit_target.date if take_profit_target else None 
    
    model['entry_value'] = entry_target.value if entry_target else None
    model['entry_index'] = entry_target.index if entry_target else None
    model['entry_date'] = entry_target.date if entry_target else None
    history.append(model)

    return history

#strategy_1
async def backtest_with_money_strategy_1(predicts: list[Predict], my_money: float, close_tp: int=0, showPrint: bool=False, positionSize: float= 100):
   
    initial_my_money = my_money
    total_opening_orders = 0


    # profit
    profit_total = 0
    profit_count = 0

    # loss
    loss_total = 0
    loss_count = 0


    # pending
    pending_total = 0
    pending_count = 0

    # canceled
    canceled_count = 0

    history = []

    for i, pr in enumerate(predicts):

        if pr.status.name == PostStatusValues.CANCELED.value:
            canceled_count += 1
            continue
        

        entries = await sync_to_async(
            lambda: list(EntryTarget.objects.filter(post=pr.post, active=True).order_by('index'))
        )()

        if pr.status.name == PostStatusValues.PENDING.value:
            pending_count += 1
            
            if len(entries) >= 1:
                total_opening_orders += 1
                my_money -= positionSize
                pending_total += positionSize
                history = historyController(history=history, predict=pr, curr_money= my_money)
            continue
        

        first_entry = entries[0]

        my_money -= positionSize
        total_opening_orders += 1


        if pr.status.name == PostStatusValues.FAILED.value:
            loss_count += 1

            loss = calProfit(positionSize, pr.profit) # is negative profit
            my_money += positionSize + loss
            loss_total += loss

            history = historyController(history=history, predict=pr, curr_money= my_money, profit=loss, entry_target=first_entry)
            continue


        take_profits = await sync_to_async(
            lambda: list(TakeProfitTarget.objects.filter(post=pr.post, active=True).order_by('index'))
        )()


        if pr.status.name == PostStatusValues.SUCCESS.value or pr.status.name == PostStatusValues.FULLTARGET.value:
            profit_count += 1

            tp = take_profits[close_tp if len(take_profits)-1 >= close_tp else -1]

            profit = calProfit(positionSize, tp.profit) # is positive profit
            
            my_money += positionSize + profit
            profit_total += profit 

            history = historyController(history=history, predict=pr, curr_money= my_money, profit=profit, entry_target=first_entry, take_profit_target=tp)

            continue

        if pr.status.name == PostStatusValues.FAILED_WITH_PROFIT.value:
            if len(take_profits)-1 >= close_tp:
                profit_count += 1
                
                tp = take_profits[close_tp]

                profit = calProfit(positionSize, tp.profit) # is positive profit
                
                my_money += positionSize + profit
                profit_total += profit

                history = historyController(history=history, predict=pr, curr_money= my_money, profit=profit, entry_target=first_entry, take_profit_target=tp)

            else:
                loss_count += 1
                
                loss = calProfit(positionSize, pr.profit) # is negative profit
                
                my_money += positionSize + loss
                loss_total += loss

                history = historyController(history=history, predict=pr, curr_money= my_money, profit=loss, entry_target=first_entry)


    if showPrint:
        print_colored(f"initial money: {initial_my_money}", "gold")
        print_colored(f"total_opening_orders: {total_opening_orders}", "#1da44f")
        print_colored(f"loss_total: {loss_total}", "pink")
        print_colored(f"profit_total: {profit_total}", "green")
        print_colored(f"gross: {profit_total+loss_total}", "deeppink")
        print_colored(f"pending_total: {pending_total}", "grey")
        print_colored(f"my free money: {my_money}", "orange")
        print_colored(f"my total money: {my_money+pending_total}", "#d16984")
        print_colored(f"profit_count: {profit_count}, loss_count: {loss_count}, pending_count: {pending_count}", "#a1309d")

    return history


