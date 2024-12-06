
from Shared.Constant import PostStatusValues
from PostAnalyzer.models import (
    Predict,
    TakeProfitTarget,
)
from Strategies.AbsStrategy import AbsStrategy
from Shared.Constant import PostStatusValues 
from asgiref.sync import sync_to_async
from PostAnalyzer.models import (
    Predict,
    TakeProfitTarget,
    StopLoss,
    EntryTarget,
)

# ****************************************************************************************************************************


class Strategy1(AbsStrategy):
    strategy_name = 'strategy1'

    async def backtest_with_money_strategy_1(self, predicts:list[Predict], close_tp:int=1, showPrint:bool= False, positionSize:float= 100):

        for i, pr in enumerate(predicts):
            statusName = pr.status.name

            if statusName in [PostStatusValues.CANCELED.value, PostStatusValues.ERROR.value, PostStatusValues.WAIT_MANY_DAYS.value]:
                continue

            
            start_timestamp = int(pr.date.timestamp() * 1000)

            # current money
            self.current_money += self.checkFreeMoneyManagement(start_timestamp)

            # blocked money
            self.total_pending_money = self.checkFBlockedMoneyManagement()

            if showPrint:
                print(f'{pr.symbol.name}, current_money: {round(self.current_money,2)}, blocked_money: {round(self.total_pending_money,2)}')


            # missed order :(
            if self.current_money < positionSize:
                if showPrint:
                    print(pr.symbol.name, 'missed\n')

                self.addMissOrder(order=pr)
                
                continue 

            profit = 0


            # get take-profits 
            all_active_take_profit = await sync_to_async(
                lambda: list(TakeProfitTarget.objects.filter(predict=pr, active =True).order_by('index'))
            )()
            all_take_profit = await sync_to_async(
                lambda: list(TakeProfitTarget.objects.filter(predict=pr).order_by('index'))
            )()
            
            active_tp_len = len(all_active_take_profit)
            tp_len = len(all_take_profit)

            is_fulltarget = active_tp_len > 0 and active_tp_len == tp_len

            is_success = is_fulltarget or (active_tp_len > 0 and active_tp_len >= close_tp)
            # print(is_success)

            if is_success:
                index = tp_len if (is_fulltarget and active_tp_len <= close_tp) else close_tp
                index -= 1
                active_take_profit = await sync_to_async(TakeProfitTarget.objects.get)(predict=pr, index=index)
                # print(active_take_profit.index, active_take_profit.profit)
            

            active_entry = await sync_to_async(
                lambda: list(EntryTarget.objects.filter(predict=pr, active=True).order_by('index'))
            )()
            
            # get stoploss 
            stoploss = await sync_to_async(StopLoss.objects.get)(predict=pr)


            # add positionSize to pending money
            self.total_pending_money += positionSize
            self.pending_count += 1
            # it reduces current_money for creating order
            self.current_money -= positionSize

            if showPrint:
                print(f'money_taken: {positionSize}, current_money: {round(self.current_money, 2)}')


            # the order has been sent and submitted, so added to active orders
            self.addActiveOrder(order=pr, positionSize=positionSize)

            # the order`s status is pending, so added to pending orders
            self.addPendingOrder(pr)

            is_hit = False
            

            if is_success:
                is_hit = True

                profit = active_take_profit.profit/100
                profit_money_value = positionSize * profit
                money_back = positionSize + profit_money_value
                self.total_opening_orders += 1

                
                date = int(active_take_profit.date.timestamp()*1000)
                self.updateMoneyManagement(id=pr.id, end_date=date, money_back=money_back)
                self.removeFromPending(order=pr)
                self.addEntryOrder(order=pr, active_date=int(active_entry[0].date.timestamp()*1000))
                self.addProfitOrder(order=pr, profit=profit, status_date=date, position_size=positionSize, money_back=money_back, type=index)
            
            elif statusName == PostStatusValues.SUCCESS.value:
                is_hit = True
                profit = pr.profit/100
                profit_money_value = positionSize * profit
                money_back = positionSize + profit_money_value
                self.total_opening_orders += 1

                date = int(all_active_take_profit[-1].date.timestamp()*1000)
                self.updateMoneyManagement(id=pr.id, end_date=date, money_back=money_back)
                self.removeFromPending(order=pr)
                self.addEntryOrder(order=pr, active_date=int(active_entry[0].date.timestamp()*1000))
                self.addProfitOrder(order=pr, profit=profit, status_date=date, position_size=positionSize, money_back=money_back, type=index)
           

            elif statusName == PostStatusValues.FAILED.value  or (not is_success and statusName != PostStatusValues.PENDING.value):
                is_hit = True
                profit = pr.profit/100
                profit_money_value = positionSize * profit
                money_back = positionSize + profit_money_value
                self.total_opening_orders += 1
                # print(statusName)

                date = int(stoploss.date.timestamp()*1000)
                self.updateMoneyManagement(id=pr.id, end_date=date, money_back=money_back)
                self.removeFromPending(order=pr)
                self.addEntryOrder(order=pr, active_date=int(active_entry[0].date.timestamp()*1000))
                self.addLossOrder(order=pr, profit=profit, status_date=date, money_back=money_back, position_size=positionSize, type= -1)

            # self.orderDetailController(entry_targets=entry_reached, predict=pr, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)

            if profit < 0:
                self.total_loss += profit
                self.loss_count += 1
                self.pending_count -= 1
            elif profit > 0:
                self.total_profit += profit
                self.profit_count += 1
                self.pending_count -= 1

            if showPrint:

                if is_hit:
                    print(f'profit: {round(profit,2)}, money back: {round(positionSize*(1+profit), 2)}')
                    print(f'current_money: {round(self.current_money+(positionSize*(1+profit)),2)}')
                else:
                    print(f'take-profit or stoploss or entry target has not been reach completely, so pending')
                

                print('\n\n')

        self.giveBackAllActiveMoney()


            




            








