
from Strategies.AbsStrategy import AbsStrategy
from Shared.dataIO import load_historic_tohlcv_json
from Shared.helpers import findProfit
from Shared.updateOHLC_FromAPI import updateOHLC_FromAPI
from Shared.Constant import PostStatusValues, PositionSideValues
from asgiref.sync import sync_to_async
from PostAnalyzer.models import (
    Predict,
    TakeProfitTarget,
    EntryTarget,
    StopLoss
)


class Strategy10(AbsStrategy):
    strategy_name = 'strategy10'

    #strategy_10
    async def backtest_with_money_strategy_10(self, predicts:list[Predict], close_tp:int=1, showPrint:bool= False, positionSize:float= 100):
        
        for i, pr in enumerate(predicts):
            try:
                if pr.status.name in [PostStatusValues.CANCELED.value, PostStatusValues.ERROR.value, PostStatusValues.WAIT_MANY_DAYS.value]:
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

                # get entries 
                entry_price = await sync_to_async(
                    lambda: list(EntryTarget.objects.filter(predict=pr).order_by('index'))
                )()

                # get take-profits 
                take_profit = await sync_to_async(
                    lambda: list(TakeProfitTarget.objects.filter(predict=pr).order_by('index'))
                )()
                # get stoploss 
                stoploss = await sync_to_async(StopLoss.objects.get)(predict=pr)

                
                # load data from JSON file
                await updateOHLC_FromAPI(start_timestamp, pr.symbol.name, pr.market.name)
                LData = load_historic_tohlcv_json(pr.symbol.name, pr.market.name)

                tp_turn = 0
                tp = take_profit[tp_turn].value
                tps = []

                new_entry = entry_price[0].value
                entry_reached = []
                wait_for_entry = True

                profit = 0

                stop_loss_reached = None
                stop_loss = stoploss.value
                # to find percent(%) off loss
                stop_loss_percent = -findProfit(new_entry,stop_loss,pr.leverage, False)
                
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

                # a flag that shows if the order hits a stoploss or fulltarget
                is_hit = False

                
                # tohlcv guide
                # row[0] = timestamp
                # row[1] = open
                # row[2] = high
                # row[3] = low
                # row[4] = close
                # row[5] = volume
                if pr.position.name == PositionSideValues.LONG.value:
                    for row in LData:
                        # continue until reach to start time of order message
                        if row[0] < start_timestamp:
                            continue
                        
                        # wait until entry of order hits (LONG)
                        if wait_for_entry and float(row[3]) <= new_entry:
                            # so remove order from pending list
                            self.removeFromPending(pr)
                            
                            # add entry
                            entry_reached.append({
                                'value': new_entry,
                                'tohlcv': row
                            })
                            # it reduces total_pending_money due to order has been opened
                            self.total_pending_money -= positionSize
                            # adding total_opening_orders
                            self.total_opening_orders += 1
                            
                            # update active_orders (start_date)
                            self.updateMoneyManagement(id=pr.id, start_date=row[0])
                            # update orders_status (start_date)
                            self.addEntryOrder(order=pr, active_date=row[0])
                        
                            # close flag for waiting
                            wait_for_entry = False
                            continue

                        # the entry has been touched, so waiting for stoploss or take-profit
                        if bool(entry_reached) and not wait_for_entry:
                            # check stoploss (LONG)
                            if float(row[3]) <= stop_loss:
                                # now the status of order is LOSS, so stoploss has been reached
                                self.pending_count -= 1
                                self.loss_count += 1
                                is_hit = True

                                # calculate the amount of loss
                                profit += -findProfit(new_entry, stop_loss, pr.leverage, False) 
                                profit_money_value = positionSize * profit
                                money_back = positionSize + profit_money_value

                                # add stop loss
                                stop_loss_reached = {
                                    'value': new_entry,
                                    'tohlcv': row
                                }
                                
                                # update active_orders (end_date, money_back)
                                self.updateMoneyManagement(id=pr.id, end_date=row[0], money_back=money_back)

                                # update orders_status. LOSS order :(
                                self.addLossOrder(order=pr, profit=profit, status_date=row[0], position_size=positionSize, money_back=money_back, type= -1 if len(tps) == 0 else len(tps))
                                break

                            if float(row[2]) >= tp: 
                                # calculate the amount of profit
                                profit += findProfit(new_entry, tp, pr.leverage, False) 
                                profit_money_value = positionSize * profit
                                money_back = positionSize + profit_money_value
                                
                                # set new entry
                                new_entry = take_profit[tp_turn].value

                                tps.append({
                                    'value': tp,
                                    'tohlcv': row
                                })
                                tp_turn += 1

                                if (tp_turn) == len(take_profit) or close_tp <= len(tps):
                                    self.pending_count -= 1
                                    self.profit_count += 1

                                    self.updateMoneyManagement(id=pr.id, end_date=row[0], money_back=money_back)
                                    self.addProfitOrder(order=pr, profit=profit, status_date=row[0],position_size=positionSize, money_back=money_back, type= 1000 if (tp_turn) == len(take_profit) else tp_turn)
                                    is_hit = True
                                    break

                                self.updateMoneyManagement(id=pr.id, money_back=money_back)
                                self.addProfitOrder(order=pr, profit=profit, status_date=row[0], type=tp_turn, position_size=positionSize,money_back=money_back)
                                tp = take_profit[tp_turn].value
                                stop_loss = round(((stop_loss_percent*new_entry)/pr.leverage)+new_entry, 5) 

                else:
                    for row in LData:
                        if row[0] < start_timestamp:
                            continue

                        if wait_for_entry and float(row[2]) >= new_entry:
                            self.removeFromPending(pr)
                            entry_reached.append({
                                'value': new_entry,
                                'tohlcv': row
                            })
                            self.total_pending_money -= positionSize
                            self.total_opening_orders += 1
                            self.updateMoneyManagement(id=pr.id, start_date=row[0])
                            self.addEntryOrder(order=pr, active_date=row[0])

                            wait_for_entry = False

                            continue

                        if bool(entry_reached) and not wait_for_entry:
                            if float(row[2]) >= stop_loss:
                                self.pending_count -= 1
                                self.loss_count += 1

                                # calculate the amount of loss
                                profit += -findProfit(new_entry, stop_loss, pr.leverage, False) 
                                profit_money_value = positionSize * profit
                                money_back = positionSize + profit_money_value

                                is_hit = True
                                stop_loss_reached = {
                                    'value': new_entry,
                                    'tohlcv': row
                                }
                                self.updateMoneyManagement(id=pr.id, end_date=row[0], money_back=money_back)
                                self.addLossOrder(order=pr, profit=profit, status_date=row[0], position_size=positionSize, money_back=money_back, type= -1 if len(tps) == 0 else len(tps))
                                break

                            if float(row[3]) <= tp:
                                # wait_for_entry = True

                                profit += findProfit(new_entry, tp, pr.leverage, False) 
                                profit_money_value = positionSize * profit
                                money_back = positionSize + profit_money_value
                                
                                new_entry = take_profit[tp_turn].value

                                tps.append({
                                    'value': tp,
                                    'tohlcv': row
                                })
                                tp_turn += 1

                                if (tp_turn) == len(take_profit) or close_tp <= len(tps):
                                    self.pending_count -= 1
                                    self.profit_count += 1
                                    self.updateMoneyManagement(id=pr.id, end_date=row[0], money_back=money_back)
                                    self.addProfitOrder(order=pr, profit=profit, status_date=row[0], position_size=positionSize, money_back=money_back, type= 1000 if (tp_turn) == len(take_profit) else tp_turn)
                                    is_hit = True
                                    break

                                self.updateMoneyManagement(id=pr.id, money_back=money_back)
                                self.addProfitOrder(order=pr, profit=profit, status_date=row[0], type=tp_turn, position_size=positionSize, money_back=money_back)

                                tp = take_profit[tp_turn].value
                                stop_loss = round((((stop_loss_percent*new_entry)/pr.leverage) * -1)+new_entry, 5) 

                self.orderDetailController(entry_targets=entry_reached, predict=pr, stopLoss=stop_loss, take_profit_targets=tps, stopLoss_time=stop_loss_reached)

                if profit < 0:
                    self.total_loss += profit
                else:
                    self.total_profit += profit
                # stat = {"tps": tps, "entry_reached": entry_reached, "stop_loss_reached": stop_loss_reached}
                # print(stat)
                if showPrint:

                    if is_hit:
                        print(f'profit: {round(profit,2)}, money back: {round(positionSize*(profit+1), 2)}')
                        print(f'current_money: {round(self.current_money+(positionSize*(profit+1)),2)}')
                    else:
                        print(f'take-profit or stoploss or entry target has not been reach completely, so pending')
                    

                    print('\n\n')

            except Exception as e:
                print("ERROR Happen", e)

        self.giveBackAllActiveMoney()


        return self.history
        

