
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
            take_profit = await sync_to_async(
                lambda: list(TakeProfitTarget.objects.filter(predict=pr).order_by('index'))
            )()

            active_take_profit = await sync_to_async(
                lambda: list(TakeProfitTarget.objects.filter(predict=pr, active=True).order_by('index'))
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
            
            tp_len = len(take_profit)
            active_tp_len = len(active_take_profit)
            is_fulltarget = active_tp_len >= close_tp

            if close_tp > tp_len:
                is_fulltarget = tp_len == active_tp_len

            # if (active_tp_len < close_tp) and (tp_len != active_tp_len):
            #     continue


            if is_fulltarget or (statusName == PostStatusValues.SUCCESS.value):
                is_hit = True

                profit = active_take_profit[active_tp_len-1].profit/100
                date = int(active_take_profit[active_tp_len-1].date.timestamp()*1000)
                self.updateMoneyManagement(id=pr.id, end_date=date, money_back=positionSize*(1+profit))
                self.addProfitOrder(order=pr, profit=profit, status_date=date, type= active_tp_len if statusName == PostStatusValues.SUCCESS.value else 1000)

            elif statusName in [PostStatusValues.FAILED_WITH_PROFIT.value, PostStatusValues.FAILED.value]:
                is_hit = True
                profit = pr.profit/100
                date = int(stoploss.date.timestamp()*1000)
                self.updateMoneyManagement(id=pr.id, end_date=date, money_back=positionSize*(1+profit))
                self.addLossOrder(order=pr, profit=profit, status_date=date)

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
                    print(f'profit: {round(profit,2)} %, money back: {round(positionSize*(1+profit), 2)}')
                    print(f'current_money: {round(self.current_money+(positionSize*(1+profit)),2)}')
                else:
                    print(f'take-profit or stoploss or entry target has not been reach completely, so pending')
                

                print('\n\n')

        self.giveBackAllActiveMoney()


            




            








