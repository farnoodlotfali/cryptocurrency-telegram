from Channels.AbsChannel import AbsChannel
import re
from telethon.tl.types import Message
from dotenv import dotenv_values
from typing import Optional
from datetime import datetime
from PostAnalyzer.models import (
    Channel,
    EntryTarget,
    Market,
    Post,
    PostStatus,
    Predict,
    Symbol,
    TakeProfitTarget,
    SettingConfig,
    PositionSide,
    MarginMode,
    StopLoss
)
from Shared.helpers import returnSearchValue, print_colored, subtractTime, findProfit, find_nearest_number_for_coienex_leverage
from Shared.Exchange import exchange
from Shared.findSameSignal import findSameSignal
from Shared.findShortOrderStat import findShortOrderStat
from Shared.findLongOrderStat import findLongOrderStat
from Shared.types import Stat
from Shared.Constant import PostStatusValues, PositionSideValues, MarginModeValues, MarketValues, OrderSide, OrderType
from Shared.updateEntryInMarketValue import updateEntryInMarketValue
from Shared.updateStoplossByEntry import updateStoplossByEntry
from Shared.updateTakeProfitByEntry import updateTakeProfitByEntry

# ****************************************************************************************************************************

_config = dotenv_values(".env")
# abs ==> abstract
class RoseChannel(AbsChannel):
    _channel_id = _config["CHANNEL_ROSE"]

    max_day_wait:int = 10

    max_profit_percent:float = 170

    # abs
    def isPredictMsg(self, msg)->bool:
        patterns = [
            r"#(\w+)",
        ]

        check = all(re.search(pattern, msg, re.IGNORECASE) for pattern in patterns)
        
        check1 = False
        if "short" in msg.lower() or "buy" in msg.lower():
            check1 = True

        # Check if all patterns have a value
        return check1 and check

    # abs
    async def findSymbol(self, msg, market)-> Optional[Symbol]:
        symbol = re.search(r"#(\w+)", msg, re.IGNORECASE)
        try:
            return await Symbol.objects.aget(base=returnSearchValue(symbol).upper(), market=market)
        except:
            return None
        
    # abs
    async def findMarket(self, msg)-> Optional[Market]:
        try:
            market_value = await Market.objects.aget(name=MarketValues.FUTURES.value.upper())
            return market_value
        except:
            return None

    # abs
    async def findPosition(self, msg)-> Optional[PositionSide]:
        pos = None
        if "short" in msg.lower():
            pos = PositionSideValues.SHORT.value
        elif "buy" in msg.lower():
            pos = PositionSideValues.LONG.value
        
        try:
            position_value = await PositionSide.objects.aget(name=pos.upper())
            return position_value
        except:
            return None
    
    # abs
    async def findLeverageAndMarginMode(self, msg)-> tuple[Optional[MarginMode], Optional[int]]:
        margin_mode = await MarginMode.objects.aget(name=MarginModeValues.ISOLATED.value.upper())
        leverage_value = int(3)    
        
        return margin_mode, leverage_value
    
    # abs
    def findStopLoss(self, msg)-> Optional[float]:
       
        return 1

    # abs
    def findEntryTargets(self, msg)-> Optional[list[float]]:

        return [OrderType.MARKET.value]
    
    # abs
    def findTakeProfits(self, msg)-> Optional[list[float]]:
       
        return [1]
            
    # abs
    async def isCancel(self, post:Post)-> bool:
        if post is None or post.reply_to_msg_id is None:
            return False
        
        try:
            manually_cancel_patterns = [
                r"Cancelled",
                r"Manually",
            ]  
            cancel_pattern =[
                r"کنسل"
            ]

            # check = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in cancel_before_patterns)
            check1 = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in manually_cancel_patterns)
            check2 = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in cancel_pattern)
         
            if check1 or check2:
                
                predict = await Predict.objects.aget(post__message_id=post.reply_to_msg_id)
                
                status_value = await PostStatus.objects.aget(name=PostStatusValues.CANCELED.value)
            
                predict.status = status_value
                predict.profit = 0
            
                await predict.asave()
                await EntryTarget.objects.filter(predict=predict).aupdate(active=False, date=None, period=None)
                await TakeProfitTarget.objects.filter(predict=predict).aupdate(active=False, date=None, period=None)
                await StopLoss.objects.filter(predict=predict).aupdate(date=None, period=None)
                return True
                
            else:
                return False
            
        except:
            # error_msg.append(model_to_dict(post))
            return False

   

    # ****************************************************************************************************************************
    # ******************************************** methods for automatic trading *************************************************
    # ****************************************************************************************************************************
    # abs
    async def predictParts(self, string, post:Post)-> Optional[Predict]:
        if string is None or post is None:
            return None
            
        try:
            
            # market
            market_value= await self.findMarket(string)
            isSpot = market_value.name == MarketValues.SPOT.value

            # symbol
            symbol_value = await self.findSymbol(string, market_value)

            # position, leverage, marginMode
            position_value = None
            leverage_value = None
            marginMode_value = None
            if not isSpot:
                position_value = await self.findPosition(string)
                marginMode_value, leverage_value = await self.findLeverageAndMarginMode(string)
            else:
                position_value= await PositionSide.objects.aget(name=PositionSideValues.BUY.value)
            
            # stopLoss
            stopLoss_value = self.findStopLoss(string)

            # entry targets
            entry_targets_value = self.findEntryTargets(string)

            # status    
            status_value = await PostStatus.objects.aget(name=PostStatusValues.PENDING.value)

            # take_profit targets
            take_profit_targets_value = self.findTakeProfits(string)

            # return Error RR < 0.2
            # TODO will add to setting, to get min RR
            # RR = findRiskToReward(entry_targets_value, take_profit_targets_value, stopLoss_value)
            
            # if RR < 0.2 or RR > 4:
            #     status_value = await sync_to_async(PostStatus.objects.get)(name="ERROR")

            # TODO check post.channel.id
            # return false if signal already exists
            # is_same_signal = await findSameSignal(post.date, symbol_value,market_value,position_value, leverage_value, marginMode_value,stopLoss_value,
            #                             take_profit_targets_value,entry_targets_value,post.channel.id)
            # if is_same_signal:
            #     return False

            # set predict object to DB
            PredictData = {
                "post": post,
                "date": post.date,
                "symbol": symbol_value,
                "position": position_value,
                "market": market_value,
                "leverage": leverage_value,
                "margin_mode": marginMode_value,
                "profit": 0,
                "status": status_value, 
                "order_id": None,
            }


            newPredict = Predict(**PredictData)
            await newPredict.asave()
            first_entry_value = entry_targets_value[0]
            
            stoploss = StopLoss(
                **{
                    "predict": newPredict,
                    "value": stopLoss_value,
                    "period": None,
                    "date": None,
                    "profit": findProfit(first_entry_value, stopLoss_value, leverage_value)*(-1),
                }
            )
            await stoploss.asave()


            # set entry value objects to DB
            if entry_targets_value:
                for i, value in enumerate(entry_targets_value):
                    
                    entryData = EntryTarget(
                        **{
                            "predict": newPredict,
                            "index": i,
                            "value": value,
                            "active": False,
                            "period": None,
                            "date": None,
                        }
                    )
                    await entryData.asave()
            
            # set tp value objects to DB
            first_tp_value = None
            if take_profit_targets_value:
                for i, value in enumerate(take_profit_targets_value):
                    if i == 0:
                        first_tp_value = value

                    takeProfitData = TakeProfitTarget(
                        **{
                            "predict": newPredict,
                            "index": i,
                            "value": value,
                            "active": False,
                            "period": None,
                            "profit": findProfit(first_entry_value, value, leverage_value),
                            "date": None,
                        }
                    )
                    await takeProfitData.asave()


            if position_value.name == PositionSideValues.SHORT.value:
                side = OrderSide.SELL.value
            else:
                side = OrderSide.BUY.value

            # create order in exchange
            order_id = await self.createOrderInExchange(symbol=symbol_value.name, entry=first_entry_value,
                                        leverage=leverage_value, side=side, type=OrderType.LIMIT.value, 
                                        stoploss=stopLoss_value, takeProfit=first_tp_value, channel=post.channel,
                                        position=position_value.name, isSpot=isSpot)
            
            # save orderId in DB
            newPredict.order_id = order_id
            await newPredict.asave()

            
            return newPredict
        except:
            
            # error_msg.append(model_to_dict(post))
            return None

    #abs
    async def extractDataFromMessage(self, message):
        
        if isinstance(message, Message):
            is_predict_msg = self.isPredictMsg(message.message)
            channel = await Channel.objects.aget(channel_id=message.peer_id.channel_id)
            PostData = {
                "channel": channel if channel else None,
                "date": message.date,
                "message_id": message.id,
                "message": message.message,
                "reply_to_msg_id": message.reply_to.reply_to_msg_id
                if message.reply_to
                else None,
                "edit_date": message.edit_date,
                "is_predict_msg": is_predict_msg,
            }
            post = Post(**PostData)

            await post.asave()
            # predict msg
            if is_predict_msg:
                await self.predictParts(message.message, post)
            # cancel msg
            elif await self.isCancel(post):
                await self.cancelOrderEx(post)
                
                
            return PostData
        else:
            return None 
        

    # ****************************************************************************************************************************
    # ******************************************** statistics methods ************************************************************
    # ****************************************************************************************************************************

    # abs
    async def statistic_PredictParts(self, string, post:Post):
        if string is None or post is None:
            return None
        
        try:
            should_check = True

            # market
            market_value= await self.findMarket(string)
            isSpot = market_value.name == MarketValues.SPOT.value

            # symbol
            symbol_value = await self.findSymbol(string, market_value)

            # position, leverage, marginMode
            position_value = None
            leverage_value = None
            marginMode_value = None
            if not isSpot:
                position_value = await self.findPosition(string)
                marginMode_value, leverage_value = await self.findLeverageAndMarginMode(string)
            else:
                position_value = await PositionSide.objects.aget(name=PositionSideValues.BUY.value)
            
            isSHORT = position_value.name == PositionSideValues.SHORT.value


            # entry targets
            entry_targets_value = self.findEntryTargets(string)
            entry_targets_value = await updateEntryInMarketValue(symbolName=symbol_value.name, entry_price=entry_targets_value, start_timestamp=int(post.date.timestamp() * 1000))
           
            # stopLoss
            stopLoss_value = updateStoplossByEntry(entry_price=entry_targets_value, leverage=1, isShort=position_value.name, max_percent_stoploss=1)
            
            # status    
            status_value = await PostStatus.objects.aget(name=PostStatusValues.PENDING.value)

            # take_profit targets
            take_profit_targets_value = updateTakeProfitByEntry(entry_price=entry_targets_value, leverage=1, isShort=position_value.name, max_percent_stoploss=1)

            
            # return Error RR < 0.2
            # TODO will add to setting, to get min RR. and it should be implement in findError method or test method in AbsChannel class
            # RR = findRiskToReward(entry_targets_value, take_profit_targets_value, stopLoss_value)
            
            # if RR < 0.2 or RR > 4:
            #     status_value = await sync_to_async(PostStatus.objects.get)(name="ERROR")
            #     should_check = False
            
            # return false if signal already exists
            is_same_signal = await findSameSignal(post.date, symbol_value,market_value,position_value, leverage_value, marginMode_value,stopLoss_value,
                                        take_profit_targets_value,entry_targets_value,post.channel.channel_id)
            if is_same_signal:
                return False
            
            print(f'symbol: {symbol_value.name}, po: {position_value.name}, stop: {stopLoss_value}, en: {entry_targets_value[0]}, tp: {take_profit_targets_value[0]}')
            first_entry_value = entry_targets_value[0]
            
            if should_check:
                if not isSHORT:
                    stat: Stat = await findLongOrderStat(stop_loss=stopLoss_value,
                                    entry_price=entry_targets_value,
                                    symbolName=symbol_value.name,
                                    take_profit=take_profit_targets_value,
                                    start_timestamp= int(post.date.timestamp() * 1000),
                                    marketName=market_value.name,
                                    max_day_wait=self.max_day_wait)
                elif isSHORT:
                    stat: Stat = await findShortOrderStat(stop_loss=stopLoss_value,
                                    entry_price=entry_targets_value,
                                    symbolName=symbol_value.name,
                                    take_profit=take_profit_targets_value,
                                    start_timestamp= int(post.date.timestamp() * 1000),
                                    marketName=market_value.name,
                                    max_day_wait=self.max_day_wait)
            else:
                stat: Stat = {"tps": [], "entry_reached": [], "stop_loss_reached": None, "break_reason": None}
            
            print(stat)
            # stat['name'] = f'{symbol_value.name}, {position_value.name}'
            print_colored("********************************************************************************************************************","#0f0")
            tps_length = len(stat['tps'])
            profit_value = 0

            if stat['break_reason']:
                status_value = await PostStatus.objects.aget(name=PostStatusValues.WAIT_MANY_DAYS.value)

            elif stat['stop_loss_reached']:
                if tps_length > 0:
                    status_value = await PostStatus.objects.aget(name=PostStatusValues.FAILED_WITH_PROFIT.value, type=tps_length)
                else:
                    status_value = await PostStatus.objects.aget(name=PostStatusValues.FAILED.value)
                profit_value = findProfit(first_entry_value, stopLoss_value, leverage_value)*(-1) 
            
            else:
                if tps_length == len(take_profit_targets_value):
                    status_value = await PostStatus.objects.aget(name=PostStatusValues.FULLTARGET.value)
                    profit_value = findProfit(first_entry_value, take_profit_targets_value[tps_length-1], leverage_value) 

                elif tps_length > 0:
                    status_value = await PostStatus.objects.aget(name=PostStatusValues.SUCCESS.value, type=tps_length)
                    profit_value = findProfit(first_entry_value, take_profit_targets_value[tps_length-1], leverage_value) 
                

            # set predict object to DB
            PredictData = {
                "post": post,
                "date": post.date,
                "symbol": symbol_value,
                "position": position_value,
                "market": market_value,
                "leverage": leverage_value,
                "margin_mode": marginMode_value,
                "profit": profit_value,
                "status": status_value, 
                "order_id": None,
            }
            newPredict = Predict(**PredictData)
            await newPredict.asave()

            # set the stoploss
            date = None
            period = None
            if stat['stop_loss_reached']:
                time = int(stat['stop_loss_reached'][0])
                date = datetime.fromtimestamp(time/ 1000)
                period = subtractTime(time, int(newPredict.date.timestamp() * 1000))

            stoploss = StopLoss(
                **{
                    "predict": newPredict,
                    "value": stopLoss_value,
                    "period": period,
                    "date": date,
                    "profit": findProfit(first_entry_value, stopLoss_value, leverage_value)*(-1),
                }
            )
            await stoploss.asave()

            # set entry value objects to DB
            if entry_targets_value:
                entriesLen = len(stat['entry_reached'])
                for i, value in enumerate(entry_targets_value):
                    isActive = i < entriesLen 
                    date = None
                    period = None
                    if isActive:
                        time = int(stat['entry_reached'][i][0])
                        date = datetime.fromtimestamp(time/ 1000)
                        period = subtractTime(time, int(newPredict.date.timestamp() * 1000))
                    entryData = EntryTarget(
                        **{
                            "predict": newPredict,
                            "index": i,
                            "value": value,
                            "active": isActive,
                            "period": period,
                            "date": date,
                        }
                    )
                    await entryData.asave()
            
            # # set tp value objects to DB
            if take_profit_targets_value:
                tpLen = len(stat['tps'])

                for i, value in enumerate(take_profit_targets_value):
                    isActive = i < tpLen 
                    date = None
                    period = None
                    if isActive:
                        time = int(stat['tps'][i][0])
                        date = datetime.fromtimestamp(time/ 1000)
                        period = subtractTime(time, int(newPredict.date.timestamp() * 1000))

                    takeProfitData = TakeProfitTarget(
                        **{
                            "predict": newPredict,
                            "index": i,
                            "value": value,
                            "active": isActive,
                            "period": period,
                            "profit": findProfit(first_entry_value, value, leverage_value),
                            "date": date,
                        }
                    )
                    await takeProfitData.asave()


            
            return newPredict
        except Exception as e:
            super().handleError(post, f"error in statisticPredictParts method {str(e)}", post.channel.name)
            return False
        
    # abs
    async def statistic_extractDataFromMessage(self, message):
        if isinstance(message, Message):
            channel = await Channel.objects.aget(
                channel_id=message.peer_id.channel_id
            )
            
            existing = await Post.objects.filter(message_id=message.id, channel=channel).aexists()
            if existing:
                return None
            
            is_predict_msg = self.isPredictMsg(message.message)

            PostData = {
                "channel": channel if channel else None,
                "date": message.date,
                "message_id": message.id,
                "message": message.message,
                "reply_to_msg_id": message.reply_to.reply_to_msg_id
                if message.reply_to
                else None,
                "edit_date": message.edit_date,
                "is_predict_msg": is_predict_msg,
            }
            post = Post(**PostData)

            await post.asave()
        
            # # predict msg
            if is_predict_msg:
                # testing predicted msg
                test_res, error_message = await self.test(message.message)
                if test_res:
                    await self.statistic_PredictParts(message.message, post)
                else:
                    super().handleError(post, error_message, channel.name)

            # # cancel msg
            elif await self.isCancel(post):
                pass
        
                
            return PostData
        else:
            return None

  