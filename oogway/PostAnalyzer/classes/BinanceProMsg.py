import math
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
)
from ..Utility.utils import returnSearchValue
from .BingXApiClass import BingXApiClass

# ****************************************************************************************************************************


class BinanceProMsg:
    bingx = BingXApiClass()

    # find position
    def findPosition(self, msg):
        if msg.find("📈") != -1:
            return "LONG"
        elif msg.find("📉") != -1:
            return "SHORT"
        return None

    # determine if a message is a predict message or not
    def isPredictMsg(self, msg):
        patterns = [
            r"🔥 #(.+)",
            r"Take-Profit:",
            r"Entry(.+)",
        ]

        return all(re.search(pattern, msg) for pattern in patterns)

    # check if post is a Take-Profit point or not
    async def isTakeProfit(self, PostData):
        if PostData is None or PostData.reply_to_msg_id is None:
            return None

        patterns = [
            r"Price(.+)",
            r"Profit(.+)",
        ]

        # Check if all patterns have a value
        check = all(re.search(pattern, PostData.message) for pattern in patterns)

        if not check:
            return False

        tp_index = re.search(r"Profit - (\d+)%", PostData.message)

        if tp_index:
            tp_index = int(returnSearchValue(tp_index))
            # the channel does not give index, so we should find out
            tp_index = math.floor(tp_index / 25) - 1
        else:
            return False

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
        if string is None or post is None:
            return None

        # symbol
        symbol_match = (
            string[string.find("#") + 1 : string.find("/USDT")].strip() + "-USDT"
        )
        symbol_value = await sync_to_async(Symbol.objects.get)(name=symbol_match)

        #  market
        market_value = await sync_to_async(Market.objects.get)(name="FUTURES")

        status_value = await sync_to_async(PostStatus.objects.get)(name="PENDING")

        # position
        position_value = self.findPosition(string)
        leverage_match = re.search(r"x(\d+)", string)
        leverage_value = returnSearchValue(leverage_match)

        # entry targets
        entry_match = re.search(r"Entry - (.+)", string)
        entry_value = returnSearchValue(entry_match)

        # stop loss
        # 5 percent of entry value(times leverage if leverage bigger than 1)
        # stopLoss_value = float(entry_value) - float(
        #     "{:.4f}".format(float(entry_value) * (0.05 / float(leverage_value)))
        # )
        stopLoss_value = float(entry_value) - float(
            "{:.4f}".format(float(entry_value) * 0.02)
        )
        # take_profit targets
        profit_values = re.findall(r"([\d.]+)\s*\(", string)

        PredictData = {
            "post": post,
            "symbol": symbol_value,
            "position": position_value,
            "market": market_value,
            "leverage": leverage_value,
            "stopLoss": stopLoss_value,
            "status": status_value,  # PENDING = 1
            "order_id": None,
        }
        newPredict = Predict(**PredictData)

        first_entry_value = entry_value
        entryData = EntryTarget(
            **{
                "post": post,
                "index": 0,
                "value": entry_value,
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

        if post.channel.can_trade:
            # set order in BingX
            crypto = newPredict.symbol.name
            size = newPredict.symbol.size
            leverage = re.findall(r"\d+", newPredict.leverage)[0]
            pos = newPredict.position
            margin_mode = self.bingx.set_margin_mode(crypto, "ISOLATED")
            set_levarage = self.bingx.set_levarage(crypto, pos, 1)
            # set_levarage = self.bingx.set_levarage(crypto, pos, leverage)

            order_data = self.bingx.open_limit_order(
                crypto,
                pos,
                first_entry_value,
                size,
                tp=first_tp_value,
                sl=newPredict.stopLoss,
            )
            newPredict.order_id = order_data["orderId"]

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
                # take profit msg
            elif await self.isTakeProfit(post):
                pass

            return PostData
        else:
            return None
