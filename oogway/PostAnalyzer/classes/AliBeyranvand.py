import re

from asgiref.sync import sync_to_async
from telethon.tl.types import Message

from ..models import (
    Channel,
    EntryTarget,
    Market,
    Post,
    PostStatus,
    Predict,
    Symbol,
    TakeProfitTarget,
    SettingConfig,
)
from ..Utility.utils import returnSearchValue
from .BingXApiClass import BingXApiClass


class AliBeyranvand:
    bingx = BingXApiClass()

    def isPredictMsg(self, msg):
        # for futures
        patterns_futures = [
            r"Futures(.+)",
            r"📌 #(.+)",
            r"Entry:(.+)",
            r"Leverage:(.+)",
            r"Stop(.+)",
            r"TP:(.+)",
        ]

        # for spot
        patterns_spot = [
            r"Spot(.+)",
            r"Buy(.+)",
            r"Pair(.+)",
            r"Stop(.+)",
            r"TP:(.+)",
        ]

        # Check if all patterns have a value
        return all(
            re.search(pattern, msg, re.IGNORECASE) for pattern in patterns_futures
        ) or all(re.search(pattern, msg, re.IGNORECASE) for pattern in patterns_spot)

    # will find position type
    def findPosition(self, msg):
        pos = None
        if "short" in msg.lower():
            pos = "SHORT"
        elif "long" in msg.lower():
            pos = "LONG"

        return pos

    # will find market name
    def findMarket(self, msg):
        market = None
        if "Futures Call".lower() in msg.lower():
            market = "FUTURES"
        elif "Spot".lower() in msg.lower():
            market = "SPOT"

        return market

    # check if post is a Take-Profit point or not
    async def isTakeProfit(self, PostData):
        if PostData is None or PostData.reply_to_msg_id is None:
            return None
        tp_index = returnSearchValue(
            re.search(r"achieved Tp(.+)", PostData.message, re.IGNORECASE)
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
            r"full(.+)",
            r"targets(.+)",
            r"achieved(.+)",
        ]

        # Check if all patterns have a value
        check = all(
            re.search(pattern, PostData.message, re.IGNORECASE) for pattern in patterns
        )

        if check:
            tp_target = await sync_to_async(TakeProfitTarget.objects.get)(
                post__message_id=PostData.reply_to_msg_id, index=tp_index
            )

            if tp_target:
                tp_target.active = True
                tp_target.date = PostData.date
                tp_target.period = None
                await sync_to_async(tp_target.save)()
                return True

        return False

    # find important parts of a predict message such as symbol or entry point
    async def predictParts(self, string, post):
        if string is None:
            return None
        
        settings = await sync_to_async(SettingConfig.objects.get)(id=1)

        #  market
        market_match = self.findMarket(string)
        market_value, market_created = await sync_to_async(
            Market.objects.get_or_create
        )(name=market_match.strip().upper())
        isSpot = market_value.name == "SPOT"

        # symbol
        symbol_match = re.search(
            r"Pair: #(.+)" if isSpot else r"📌 #(.+)", string, re.IGNORECASE
        )
        symbol_match = (
            returnSearchValue(symbol_match).strip().replace("/", "").split("USDT")[0]
        )
        symbol_value = await sync_to_async(Symbol.objects.get)(asset=symbol_match)

        # position
        position_match = "Buy" if isSpot else self.findPosition(string)
        # leverage
        leverage_match = re.search(r"Leverage: (.+)", string)
        # stopLoss
        stopLoss_match = returnSearchValue(re.search(r"Stop :(.+)", string))
        stopLoss_match = (
            float(re.search(r"\d+(\.\d+)?", stopLoss_match).group())
            if stopLoss_match
            else None
        )
        # status
        status_value = await sync_to_async(PostStatus.objects.get)(name="PENDING")

        # entry targets
        entry_targets_match = re.search(r"Entry:(.+?)\n\n", string, re.DOTALL)
        entry_values = (
            re.findall(r"\d+(?:\.\d+)?", entry_targets_match.group(1))
            if entry_targets_match
            else None
        )
        # take_profit targets
        take_profit_targets_match = re.search(r"TP:(.+?)\n\n", string, re.DOTALL)
        profit_values = (
            re.findall(r"\d+(?:\.\d+)?", take_profit_targets_match.group(1))
            if take_profit_targets_match
            else None
        )

        PredictData = {
            "post": post,
            "symbol": symbol_value,
            "position": position_match,
            "market": market_value,
            "leverage": returnSearchValue(leverage_match),
            "stopLoss": stopLoss_match,
            "status": status_value,  # PENDING = 1
        }
        newPredict = Predict(**PredictData)
        await sync_to_async(newPredict.save)()

        first_entry_value = None
        if entry_values:
            for i, value in enumerate(entry_values):
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

        first_tp_value = None
        if profit_values:
            for i, value in enumerate(profit_values):
                if i == 0:
                    first_tp_value = value
                takeProfitData = TakeProfitTarget(
                    **{
                        "post": post,
                        "index": i,
                        "value": value,
                        "active": False,
                        "period": None,
                        "date": None,
                    }
                )
                await sync_to_async(takeProfitData.save)()

        if post.channel.can_trade and settings.allow_channels_set_order :
            # set order in BingX
                max_entry_money = settings.max_entry_money

                crypto = newPredict.symbol.name
                leverage = re.findall(r"\d+", newPredict.leverage)[0]
                pos = newPredict.position
                margin_mode = self.bingx.set_margin_mode(crypto, "ISOLATED")
                # set_levarage = self.bingx.set_levarage(crypto, pos, leverage)
                set_levarage = self.bingx.set_levarage(crypto, pos, 1)

                # 2- size = float(newPredict.symbol.size) 
                # 3-
                size = max_entry_money / float(first_entry_value)
                    
                order_data = await self.open_trade(
                    crypto,
                    pos,
                    first_entry_value,
                    size,
                    sl=newPredict.stopLoss,
                    tp=first_tp_value,
                )
                newPredict.order_id = order_data["orderId"]
                

        await sync_to_async(newPredict.save)()

        return PredictData
    
    async def open_trade(self, pair, position_side, price, volume, sl, tp):
        print(price, volume, "tp: ",tp,"sl: ", sl, position_side)
        order_data = self.bingx.open_limit_order(
            pair,
            position_side,
            price,
            volume,
            sl,
            tp,
        )

        return order_data


    async def extract_data_from_message(self, message):
        if isinstance(message, Message):
            is_predict_msg = self.isPredictMsg(message.message)
            channel = await sync_to_async(Channel.objects.get)(
                channel_id=message.peer_id.channel_id
            )
            PostData = {
                "channel": channel,
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
            #     # take profit msg
            elif await self.isTakeProfit(post):
                pass

            return PostData
        else:
            return None
