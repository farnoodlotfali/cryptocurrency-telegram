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
            r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT",
            r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)",
            r"Entry (Targets|Price):([\s\S]+?)Take-Profit",
            r"Market:\s*([A-Z]+)",
            r"(StopLoss|Description):\s*([\d.]|\w+)",
        ]

        return all(re.search(pattern, msg) for pattern in patterns)

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
    
    # main method
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

            return PostData
        else:
            return None 