from Channels.AbsChannel import AbsChannel
import re
from asgiref.sync import sync_to_async
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
    MarginMode
)
from Shared.helpers import returnSearchValue, print_colored, subtractTime
from Shared.Exchange import exchange
from Shared.SymbolConverter import SymbolConverter
from Shared.findRiskToReward import findRiskToReward
from Shared.findSameSignal import findSameSignal
from Shared.findShortOrderStat import findShortOrderStat
from Shared.findLongOrderStat import findLongOrderStat

# ****************************************************************************************************************************

_config = dotenv_values(".env")
# abs ==> abstract
class FeyzianChannel(AbsChannel):
    _channel_id = _config["CHANNEL_FEYZ"]

    # abs
    def isPredictMsg(self, msg)->bool:
        patterns = [
        r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT",
        r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)",
        r"Entry (Targets|Price):([\s\S]+?)Take-Profit",
        r"Market:\s*([A-Z]+)",
        r"(StopLoss|Description):\s*([\d.]|\w+)",
        ]

        # Check if all patterns have a value
        return all(re.search(pattern, msg, re.IGNORECASE) for pattern in patterns)

    # abs
    async def findSymbol(self, msg, market)-> Optional[Symbol]:
        symbol = re.search(r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT", msg, re.IGNORECASE)
        
        try:
            return await sync_to_async(Symbol.objects.get)(base=returnSearchValue(symbol).upper(), market=market)
        except:
            return None
        
    # abs
    async def findMarket(self, msg)-> Optional[Market]:
        market_match = re.search(r"Market:\s*([A-Z]+)", msg, re.IGNORECASE)
        
        try:
            market_value = await sync_to_async(Market.objects.get)(name=returnSearchValue(market_match).upper())
            return market_value
        except:
            return None

    # abs
    async def findPosition(self, msg)-> Optional[PositionSide]:
        position_match = re.search(r"Position:\s*([A-Z]+)", msg)
        
        try:
            position_value = await sync_to_async(PositionSide.objects.get)(name=returnSearchValue(position_match).upper())
            return position_value
        except:
            return None
    
    # abs
    async def findLeverageAndMarginMode(self, msg)-> tuple[Optional[MarginMode], Optional[int]]:
        leverage_match = re.search(r"Leverage:\s*(Isolated|Cross)\s*(\d+x)", msg, re.IGNORECASE)
        if leverage_match:
            margin_mode = await sync_to_async(MarginMode.objects.get)(name=returnSearchValue(leverage_match).upper())   
            leverage_value = int(leverage_match.group(2).lower().replace("x",""))    
        else:
            margin_mode = None
            leverage_value = None
        
        return margin_mode, leverage_value
    
    # abs
    def findStopLoss(self, msg)-> Optional[float]:
        msg = msg.replace(",","")
        stoploss = returnSearchValue(re.search(r"StopLoss:\s*([\d.]+)", msg))

        return float(stoploss if stoploss else 'inf')

    # abs
    def findEntryTargets(self, msg)-> Optional[list[float]]:
        msg = msg.replace(",","")
        match = re.search(r"Entry Targets:([\s\S]+?)Take-Profit", msg, re.IGNORECASE)
        match1 = re.search(r"Entry Price:([\s\S]+?)Take-Profit", msg, re.IGNORECASE)
        final = match if match else match1
        if final:
            extracted_data = returnSearchValue(final)
            return [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", extracted_data))  if i % 2 == 1]
    
    # abs
    def findTakeProfits(self, msg)-> Optional[list[float]]:
        msg = msg.replace(",","")
        match = re.search(r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)", msg, re.IGNORECASE)
        if match:
            extracted_data = returnSearchValue(match)
            return [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", extracted_data)) if i % 2 == 1]
            
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
            
            if check1 or check2 :
                
                predict = await sync_to_async(Predict.objects.get)(
                    post__message_id=post.reply_to_msg_id
                )
                
                status_value = await sync_to_async(PostStatus.objects.get)(name="CANCELED")
            
                predict.status = status_value
                predict.profit = 0
            
                await sync_to_async(predict.save)()
                return True
                
            else:
                return False
            
        except:
            # error_msg.append(model_to_dict(post))
            return False

    # cancel order in exchange
    async def cancelOrderEx(self, post:Post)-> bool:
        if post is None or post.reply_to_msg_id is None:
            return False
        
        try:
            predict = await sync_to_async(
            lambda: Predict.objects.select_related('symbol', 'market').get(post__message_id=post.reply_to_msg_id)
            )()
            
            res = exchange.cancel_order(symbol=SymbolConverter(predict.symbol.name, predict.market.name), id=predict.order_id)
            print(res)
        
            return True
                
        except Exception as e:
            # print( e)
            super().handleError(post, f"error in cancelOrderEx method, {str(e)}", post.channel.name)
         
            return False




    # abs
    async def predictParts(self, string, post:Post)-> Optional[Predict]:
        if string is None or post is None:
            return None
        
    # try:
        settings = await sync_to_async(SettingConfig.objects.get)(id=1)
    
        # market
        market_value= await self.findMarket(string)
        isSpot = market_value.name == "SPOT"

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
            position_value= await sync_to_async(PositionSide.objects.get)(name="BUY")
        
        # stopLoss
        stopLoss_value = self.findStopLoss(string)

        # entry targets
        entry_targets_value = self.findEntryTargets(string)

        # status    
        status_value = await sync_to_async(PostStatus.objects.get)(name="PENDING")

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
            "stopLoss": stopLoss_value,
            "margin_mode": marginMode_value,
            "profit": 0,
            "status": status_value, 
            "order_id": None,
        }


        newPredict = Predict(**PredictData)

        symbol_value_conv = SymbolConverter(symbol_value.name, market_value.name)

        # set entry value objects to DB
        first_entry_value = None
        if entry_targets_value:
            for i, value in enumerate(entry_targets_value):
                if i == 0:
                    first_entry_value = value
                entryData = EntryTarget(
                    **{
                        "post": post,
                        "index": i,
                        "value": value,
                        "active": False,
                        "period": None,
                        "date": None,
                    }
                )
                await sync_to_async(entryData.save)()
        
        # set tp value objects to DB
        first_tp_value = None
        if take_profit_targets_value:
            for i, value in enumerate(take_profit_targets_value):
                if i == 0:
                    first_tp_value = value

                takeProfitData = TakeProfitTarget(
                    **{
                        "post": post,
                        "index": i,
                        "value": value,
                        "active": False,
                        "period": None,
                        "profit": round(abs(((value/first_entry_value)-1)*100*leverage_value), 5),
                        "date": None,
                    }
                )
                await sync_to_async(takeProfitData.save)()

        # create order in exchange
        if  not isSpot and post.channel.can_trade and settings.allow_channels_set_order and leverage_value <= settings.max_leverage:
            max_entry_money = settings.max_entry_money
            leverage_effect = settings.leverage_effect

            leverage_number = leverage_value if leverage_effect else 1
            position = position_value.name

            # set Margin Mode for a Pair in exchange
            exchange.set_margin_mode(marginMode="ISOLATED",symbol=symbol_value_conv)

            # set Leverage for a Pair in exchange
            exchange.set_leverage(leverage=leverage_number, symbol=symbol_value_conv,params={
                'side': position
            })

            size_volume = max_entry_money / float(first_entry_value)
            
            # set order in exchange
            print(first_entry_value, size_volume, "tp: ",first_tp_value,"sl: ", stopLoss_value, position)
            order_data = exchange.create_order(
                symbol=symbol_value_conv,
                type='limit',
                side='buy',
                amount=size_volume,
                price=first_entry_value,
                params={
                    'positionSide': position,
                    'takeProfit': {
                        "type": "TAKE_PROFIT_MARKET",
                        "quantity": size_volume,
                        "stopPrice": first_tp_value,
                        "price": first_tp_value,
                        "workingType": "MARK_PRICE"
                    },
                    'stopLoss': {
                        "type": "TAKE_PROFIT_MARKET",
                        "quantity": size_volume,
                        "stopPrice": stopLoss_value,
                        "price": stopLoss_value,
                        "workingType": "MARK_PRICE"
                    }
                }
            )
            print(order_data)

            

            # save orderId in DB
            newPredict.order_id = order_data['info']['orderId']

        await sync_to_async(newPredict.save)()
        return newPredict
    # except:
        
    #     # error_msg.append(model_to_dict(post))
    #     return None
    


    #abs, main method
    async def extractDataFromMessage(self, message):
        
        if isinstance(message, Message):
            is_predict_msg = self.isPredictMsg(message.message)
            channel = await sync_to_async(Channel.objects.get)(
                channel_id=message.peer_id.channel_id
            )
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

            await sync_to_async(post.save)()
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
            isSpot = market_value.name == "SPOT"

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
                position_value= await sync_to_async(PositionSide.objects.get)(name="BUY")
            
            # stopLoss
            stopLoss_value = self.findStopLoss(string)

            # entry targets
            entry_targets_value = self.findEntryTargets(string)

            # status    
            status_value = await sync_to_async(PostStatus.objects.get)(name="PENDING")

            # take_profit targets
            take_profit_targets_value = self.findTakeProfits(string)
            
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
            
            print(symbol_value.name, position_value.name)
            isSHORT = position_value.name == "SHORT"
            first_entry_value = entry_targets_value[0]
            
            if should_check:
                if not isSHORT:
                    stat = await findLongOrderStat(stop_loss=stopLoss_value,
                                    entry_price=entry_targets_value,
                                    symbol=symbol_value,
                                    take_profit=take_profit_targets_value,
                                    start_timestamp= int(post.date.timestamp() * 1000))
                elif isSHORT:
                    stat = await findShortOrderStat(stop_loss=stopLoss_value,
                                    entry_price=entry_targets_value,
                                    symbol=symbol_value,
                                    take_profit=take_profit_targets_value,
                                    start_timestamp= int(post.date.timestamp() * 1000))
            else:
                stat = {"tps": [], "entry_reached": [], "stop_loss_reached": None}
                
            print(stat)
            # stat['name'] = f'{symbol_value.name}, {position_value.name}'
            print_colored("********************************************************************************************************************","#0f0")
            tps_length = len(stat['tps'])
            profit_value = 0

            if stat['stop_loss_reached']:
                if tps_length > 0:
                    status_value = await sync_to_async(PostStatus.objects.get)(name="FAILED WITH PROFIT", type=tps_length)
                else:
                    status_value = await sync_to_async(PostStatus.objects.get)(name="FAILED")
                profit_value = round(((float(stopLoss_value)/float(first_entry_value))-1)*100*float(leverage_value) * (-1 if isSHORT else 1), 5)
            else:
                if tps_length == len(take_profit_targets_value):
                    status_value = await sync_to_async(PostStatus.objects.get)(name="FULLTARGET")
                    profit_value = round(abs(((take_profit_targets_value[tps_length-1]/first_entry_value)-1)*100*leverage_value), 5)

                elif tps_length > 0:
                    status_value = await sync_to_async(PostStatus.objects.get)(name="SUCCESS", type=tps_length)
                    profit_value = round(abs(((take_profit_targets_value[tps_length-1]/first_entry_value)-1)*100*leverage_value), 5)
                

            # set predict object to DB
            PredictData = {
                "post": post,
                "date": post.date,
                "symbol": symbol_value,
                "position": position_value,
                "market": market_value,
                "leverage": leverage_value,
                "stopLoss": stopLoss_value,
                "margin_mode": marginMode_value,
                "profit": profit_value,
                "status": status_value, 
                "order_id": None,
            }
            newPredict = Predict(**PredictData)

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
                        period = subtractTime(time, int(post.date.timestamp() * 1000))
                    entryData = EntryTarget(
                        **{
                            "post": post,
                            "index": i,
                            "value": value,
                            "active": isActive,
                            "period": period,
                            "date": date,
                        }
                    )
                    await sync_to_async(entryData.save)()
            
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
                        period = subtractTime(time, int(post.date.timestamp() * 1000))

                    takeProfitData = TakeProfitTarget(
                        **{
                            "post": post,
                            "index": i,
                            "value": value,
                            "active": isActive,
                            "period": period,
                            "profit": round(abs(((value/first_entry_value)-1)*100*leverage_value), 5),
                            "date": date,
                        }
                    )
                    await sync_to_async(takeProfitData.save)()


            await sync_to_async(newPredict.save)()
            return newPredict
        except:
            super().handleError(post, "error in statisticPredictParts method", post.channel.name)
            return False
        
    # abs
    async def statistic_extractDataFromMessage(self, message):
        if isinstance(message, Message):
            is_predict_msg = self.isPredictMsg(message.message)
            channel = await sync_to_async(Channel.objects.get)(
                channel_id=message.peer_id.channel_id
            )
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

            await sync_to_async(post.save)()
        
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

  