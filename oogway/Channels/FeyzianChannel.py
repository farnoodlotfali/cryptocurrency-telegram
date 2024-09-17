from Channels.AbsChannel import AbsChannel
import re
from asgiref.sync import sync_to_async
from telethon.tl.types import Message

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
from Shared.helpers import returnSearchValue
from Shared.Exchange import exchange
from Shared.SymbolConverter import SymbolConverter

# ****************************************************************************************************************************

class FeyzianChannel(AbsChannel):
    
    # determine if a message is a predict message or not
    def isPredictMsg(self, msg):
        patterns = [
            r"Symbol:\s*#?([A-Z]+)[/\s]?USDT",
            r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)",
            r"Entry (Targets|Price):([\s\S]+?)Take-Profit",
            r"Market:\s*([A-Z]+)",
            r"(StopLoss|Description):\s*([\d.]|\w+)",
        ]

        return all(re.search(pattern, msg) for pattern in patterns)

    # check if post is a Entry point or not
    async def isEntry(self, PostData):
        entry_price = returnSearchValue(
            re.search(r"Entry Price: (.+)", PostData.message)
        )

        entry_index = returnSearchValue(re.search(r"Entry(.+)", PostData.message))

        if entry_index:
            # find number
            entry_index = re.search(r"\d+", entry_index)
            if entry_index:
                entry_index = int(entry_index.group()) - 1
            else:
                return False
        else:
            return False

        patterns = [r"Entry(.+)", r"Price:(.+)", r"Entry Price: (.+)"]
        check = all(re.search(pattern, PostData.message) for pattern in patterns)

        # Check if the words "achieved" and "all" are not present
        words_absent = not re.search(r"achieved", PostData.message, re.IGNORECASE) and not re.search(r"\ball\b", PostData.message, re.IGNORECASE)
       
        # for control "average entry".
        # sometimes entry_price is different to value. so we should find difference, then calculate error
        if entry_price and check and words_absent:
            entry_price_value = float(re.findall(r"\d+\.\d+", entry_price)[0])

            entry_target = await sync_to_async(EntryTarget.objects.get)(
                post__message_id=PostData.reply_to_msg_id, index=entry_index
            )

            if entry_target:
                bigger_number = max(entry_price_value, float(entry_target.value))
                smaller_number = min(entry_price_value, float(entry_target.value))

                error = (100 * (1 - (smaller_number / bigger_number))) > 1
                if error:
                    return False
                else:
                    entry_target.active = True
                    entry_target.date = PostData.date
                    # entry_target.date = period
                    await sync_to_async(entry_target.save)()
                    return True

        return False
    
    # check if post is a AllEntryPrice point or not
    async def isAllEntryPrice(self, post):
        if post is None or post.reply_to_msg_id is None:
            return False   
        patterns = [r"all entry targets\s", r"achieved\s", r"Entry Price:\s"]
        check = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in patterns)
        
        if check:
            entry_targets = await sync_to_async(list)(
                EntryTarget.objects.filter(post__message_id=post.reply_to_msg_id)
            )
            for target in entry_targets:
                if not target.active:
                    target.active = True
                    target.date = post.date
                    await sync_to_async(target.save)()
                
    # check if post is a Stoploss point or not
    async def isStopLoss(self, post):
        if post is None or post.reply_to_msg_id is None:
            return False
        
        failed_with_profit_patterns = [
            r"stoploss\s",
            r"profit\s",
            r"reaching\s",
            r"closed\s",
        ]

        failed_patterns = [
            r"stop\s",
            r"target\s",
            r"hit\s",
            r"loss:\s",
        ]

        check = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in failed_with_profit_patterns)
        check1 = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in failed_patterns)

        if (check1):
            status_value = await sync_to_async(PostStatus.objects.get)(name="FAILED")
        elif (check):
            status_value = await sync_to_async(PostStatus.objects.get)(name="FAILED WITH PROFIT")
           
        
        if check or check1:
            predict = await sync_to_async(Predict.objects.get)(
                post__message_id=post.reply_to_msg_id
            )
            first_entry = await sync_to_async(EntryTarget.objects.get)(
                post__message_id=post.reply_to_msg_id, index=0  
            )
            position_name = await sync_to_async(lambda: predict.position.name)()
            isSHORT = position_name == "SHORT"
            predict.status = status_value
            predict.profit = round(((float(predict.stopLoss)/float(first_entry.value))-1)*100*float(predict.leverage) * (-1 if isSHORT else 1), 5)
            await sync_to_async(predict.save)()
            return True
          
        else:
            return False

    # check if post is a AllProfit point or not
    async def isAllProfitReached(self, post):
        if post is None or post.reply_to_msg_id is None:
            return False   
        patterns = [r"all take-profit\s", r"achieved\s", r"profit:\s", r"period:\s"]
        check = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in patterns)


        if check:

            take_profits = await sync_to_async(list)(
                TakeProfitTarget.objects.filter(post__message_id=post.reply_to_msg_id)
            )
            for profit in take_profits:
                if not profit.active:
                    profit.active = True
                    profit.date = post.date
                    profit.period = returnSearchValue(
                    re.search(r"Period: (.+)", post.message)
                    )
                    await sync_to_async(profit.save)()


            status_value = await sync_to_async(PostStatus.objects.get)(name="SUCCESS")
            predict_value = await sync_to_async(Predict.objects.get)(
                post__message_id=post.reply_to_msg_id
            )

            predict_value.status = status_value
            await sync_to_async(predict_value.save)()
            return True
        else:
            return False

    # check if post is a Take-Profit point or not
    async def isTakeProfit(self, PostData):
        if PostData is None or PostData.reply_to_msg_id is None:
            return None
        tp_index = returnSearchValue(
            re.search(r"Take-Profit target(.+)", PostData.message)
        )
        if tp_index:
            tp_index = re.search(r"\d+", tp_index)
            if tp_index:
                tp_index = int(tp_index.group()) - 1
            else:
                return False
        else:
            return False

        patterns = [
            r"Take-Profit(.+)",
            r"Profit(.+)",
            r"Period(.+)",
        ]

        # Check if all patterns have a value
        check = all(re.search(pattern, PostData.message) for pattern in patterns)

        if check:
            tp_target = await sync_to_async(TakeProfitTarget.objects.get)(
                post__message_id=PostData.reply_to_msg_id, index=tp_index
            )
            predict = await sync_to_async(Predict.objects.get)(
                post__message_id=PostData.reply_to_msg_id
            )

            if tp_target:
                tp_target.active = True
                tp_target.date = PostData.date
                tp_target.period = returnSearchValue(
                    re.search(r"Period: (.+)", PostData.message)
                )

                predict.profit = tp_target.profit
                
                await sync_to_async(tp_target.save)()
                await sync_to_async(predict.save)()
                return True

        return False


    async def findSymbol(self, msg):
        symbol = re.search(r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT", msg, re.IGNORECASE)
        
        try:
            return await sync_to_async(Symbol.objects.get)(asset=returnSearchValue(symbol).upper())
        except:
            return None
        
    async def findMarket(self, msg):
        market_match = re.search(r"Market:\s*([A-Z]+)", msg, re.IGNORECASE)
        
        try:
            market_value = await sync_to_async(Market.objects.get)(name=returnSearchValue(market_match).upper())
            return market_value
        except:
            return None

    async def findPosition(self, msg):
        position_match = re.search(r"Position:\s*([A-Z]+)", msg)
        
        try:
            position_value = await sync_to_async(PositionSide.objects.get)(name=returnSearchValue(position_match).upper())
            return position_value
        except:
            return None
        
    async def findLeverageAndMarginMode(self, msg):
        leverage_match = re.search(r"Leverage:\s*(Isolated|Cross)\s*(\d+x)", msg, re.IGNORECASE)
        if leverage_match:
            leverage_type = await sync_to_async(MarginMode.objects.get)(name=returnSearchValue(leverage_match).upper())   
            leverage_value = int(leverage_match.group(2).lower().replace("x",""))    
        else:
            leverage_type = None
            leverage_value = None
        
        return leverage_type, leverage_value
    
    def findStopLoss(self, msg):
        return returnSearchValue(re.search(r"StopLoss:\s*([\d.]+)", msg))

    def findEntryTargets(self, msg):
        match = re.search(r"Entry Targets:([\s\S]+?)Take-Profit", msg, re.IGNORECASE)
        match1 = re.search(r"Entry Price:([\s\S]+?)Take-Profit", msg, re.IGNORECASE)
        final = match if match else match1
        if final:
            extracted_data = returnSearchValue(final)
            return [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", extracted_data))  if i % 2 == 1]
            
    def findTakeProfits(self, msg):
        match = re.search(r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)", msg, re.IGNORECASE)
        if match:
            extracted_data = returnSearchValue(match)
            return [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", extracted_data)) if i % 2 == 1]
        
    # find important parts of a predict message such as symbol or entry point
    async def predictParts(self, string, post:Post):
        if string is None or post is None:
            return None
        
        settings = await sync_to_async(SettingConfig.objects.get)(id=1)
       
        # symbol
        symbol_value = await self.findSymbol(string)

        # market
        market_value= await self.findMarket(string)
        isSpot = market_value.name == "SPOT"

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
            "status": status_value,  # PENDING = 1
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

        if not isSpot and post.channel.can_trade and settings.allow_channels_set_order and leverage_value <= settings.max_leverage:
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
    
    async def extract_data_from_message(self, message):
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

            # entry msg
            elif await self.isEntry(post):
                pass
            # take profit msg
            elif await self.isTakeProfit(post):
                pass
            # stop loss msg
            elif await self.isStopLoss(post):
                pass
            # All Profit msg
            elif await self.isAllProfitReached(post):
                pass
            # All EntryPrice msg
            elif await self.isAllEntryPrice(post):
                pass

            return PostData
        else:
            return None 