import shutil

source_file_path = '.\..\..\.env'

destination_file_path = '.'

shutil.copy(source_file_path, destination_file_path)

import django
import os
import sys
project_path = '../../'  # Adjust this to your actual project path
sys.path.append(project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oogway.settings')
django.setup()
import asyncio
import re
from asgiref.sync import sync_to_async
from telethon.tl.types import  Message, PeerChannel
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.sync import TelegramClient, events
from tqdm import tqdm
from itertools import groupby
from datetime import datetime, timedelta, timezone
from PostAnalyzer.Utility.utils import returnSearchValue

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
import json
from django.forms.models import model_to_dict

from dotenv import dotenv_values

config = dotenv_values(".env")

api_id = config["api_id"]
api_hash = config["api_hash"]

username = config["username"]


error_msg = []

## convert to json
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        if isinstance(o, str):
            return o  # Return Persian text as is without encoding

        return json.JSONEncoder.default(self, o)


def convertToJsonFile(data, name, folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(f"./{folder_name}/{name}.json", "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, cls=DateTimeEncoder, ensure_ascii=False)


## is Predict Msg?
def isPredictMsg(msg):
    patterns = [
        r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT",
        r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)",
        r"Entry (Targets|Price):([\s\S]+?)Take-Profit",
        r"Market:\s*([A-Z]+)",
        r"(StopLoss|Description):\s*([\d.]|\w+)",
    ]

    # Check if all patterns have a value
    return all(re.search(pattern, msg, re.IGNORECASE) for pattern in patterns)
## Symbol
async def findSymbol(msg):
    symbol = re.search(r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT", msg, re.IGNORECASE)
    
    try:
        return await sync_to_async(Symbol.objects.get)(asset=returnSearchValue(symbol).upper())
    except:
        return None
## Market
async def findMarket(msg):
    market_match = re.search(r"Market:\s*([A-Z]+)", msg, re.IGNORECASE)
    
    try:
        market_value = await sync_to_async(Market.objects.get)(name=returnSearchValue(market_match).upper())
        return market_value
    except:
        return None

## Position
async def findPosition(msg):
    position_match = re.search(r"Position:\s*([A-Z]+)", msg)
    
    try:
        position_value = await sync_to_async(PositionSide.objects.get)(name=returnSearchValue(position_match).upper())
        return position_value
    except:
        return None
## Leverage and Margin Mode
async def findLeverage(msg):
    leverage_match = re.search(r"Leverage:\s*(Isolated|Cross)\s*(\d+x)", msg, re.IGNORECASE)
    if leverage_match:
        leverage_type = await sync_to_async(MarginMode.objects.get)(name=returnSearchValue(leverage_match).upper())   
        leverage_value = int(leverage_match.group(2).lower().replace("x",""))    
    else:
        leverage_type = None
        leverage_value = None
    
    return leverage_type, leverage_value
## StopLoss
def findStopLoss(msg):
   msg = msg.replace(",","")

   return returnSearchValue(re.search(r"StopLoss:\s*([\d.]+)", msg))
## Entry Targets
def findEntryTargets(msg):
    msg = msg.replace(",","")
    match = re.search(r"Entry Targets:([\s\S]+?)Take-Profit", msg, re.IGNORECASE)
    match1 = re.search(r"Entry Price:([\s\S]+?)Take-Profit", msg, re.IGNORECASE)
    final = match if match else match1
    if final:
        extracted_data = returnSearchValue(final)
        return [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", extracted_data))  if i % 2 == 1]
## Take Profits
def findTakeProfits(msg):
    msg = msg.replace(",","")
    match = re.search(r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)", msg, re.IGNORECASE)
    if match:
        extracted_data = returnSearchValue(match)
        return [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", extracted_data)) if i % 2 == 1]
        
## simple test
msg = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #AVAX/USDT\nMarket: FUTURES\nPosition: LONG\nLeverage: Isolated 3x\n\nEntry Targets: \n1) 11.80\n2) 11.502\n\nTake-Profit Targets: \n1) 12.025\n2) 12.281\n3) 12.564\n4) 12.950\n\nStopLoss: 11.19\nB.Z",    "edit_date": None,
    "media": None,
}

msg1 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #FILUSDT.P\nMarket: FUTURES\nPosition: SHORT\nLeverage: Isolated 4x\n\nEntry Targets: \n1) 5.430\n2) 5.212\n\nTake-Profit Targets: \n1) 5.517\n2) 5.608\n3) 5.715\n4) 5.823\n5) 5.982\n\nStopLoss: 5.154\nB.Z",    
    "edit_date": None,
    "media": None,
}

msg3 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #BTC/USDT Market: FUTURES Position: LONG Leverage: Isolated 6x Entry Targets: 1) 30000.54 2) 32000.43 3) 33000. Take-Profit Targets: 1) 30010.66 2) 30016 3) 30019 4) 30040 StopLoss: 29010 B.Z #test",    
    "edit_date": None,
    "media": None,
}

msg4 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #Galausdt Market: FUTURES Position: LONG Leverage: Isolated 6x Entry Targets: 1) 30000.54 2) 32000.43 3) 33000. Take-Profit Targets: 1) 30010.66 2) 30016 3) 30019 4) 30040 StopLoss: 29010 B.Z #test",    
    "edit_date": None,
    "media": None,
}

msg5 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #1000BONKUSDT.P\nMarket: FUTURES\nPosition: LONG\nLeverage: Isolated 4x\n\nEntry Targets: \n1) 0.022713\n2) 0.021730\n\nTake-Profit Targets: \n1) 0.23111\n2) 0.23689\n3) 0.24366\n4) 0.25361\n\nStopLoss: 0.21400\nB.Z",    
    "edit_date": None,
    "media": None,
}

msg6 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #GTCUSDT.P\nMarket: FUTURES\nPosition: LONG\nLeverage: Isolated 4x\nOrder Type: Limit\n\nEntry Price: \n1) 1.139\n2) 1.096\n\nTake-Profit Targets: \n1) 1.155\n2) 1.178\n3) 1.205\n4) 1.234\n5) 1.271\n\nStopLoss: 1.079\nB.Z",    
    "edit_date": None,
    "media": None,
}

msg7 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #ETHUSDT.P\nMarket: FUTURES\nPosition: LONG\nLeverage: Isolated 30x\nOrder Type: Limit\n\nEntry Price: \n1) 3,358.32\n2) 3,346.91\n\nTake-Profit Targets: \n1) 3363.43\n2) 3370.13\n3) 3376.83\n4) 3398.63\n\nStopLoss: 3,337.63\nB.Z",    
    "edit_date": None,
    "media": None,
}

# spot
msg2 = {
    "id": 3084,
    "date": "2023-12-19T12:49:50+00:00",
    "reply_to_msg_id": None,
    "message": "Symbol: #ETH/USDT\nMarket: SPOT\n\nEntry Targets: \n1) 2930.00\n2) 2870.00\n\nTake-Profit Targets: \n1) 3100.00\n2) 3200.00\n\n\nDescription: HOLD MODE\nمیان مدت\nB.Z",    
    "edit_date": None,
    "media": None,
}

string = msg7["message"]

async def pre():
    # ************* FIND IS PREDICT *************
    isPredict = isPredictMsg(string)
    print(isPredict)


    # ************* FIND SYMBOL *************
    # method 1
    # symbol_match = re.search(r"Symbol:(.+)", string)
    # symbol_match = returnValue(symbol_match).split("USDT")[0].replace("/", "").replace(" ", "").replace("#", "")
    
    # method 2
    symbol = await findSymbol(string)
    print(symbol)


    # ************* FIND MARKET *************
    market =  findMarket(string)
    print(market.name)

    if market.name != "SPOT":
        # ************* FIND POSITION *************
        position =  findPosition(string)
        print(position.name)

        # ************* FIND LEVERAGE *************
        marginMode, leverage =  findLeverage(string)
        print(marginMode.name, leverage)


    # ************* FIND STOP LOSS *************
    stopLoss = findStopLoss(string)
    print(stopLoss)

    # ************* FIND ENTRY TARGETS *************
    entries = findEntryTargets(string)
    print(entries)
    
    # ************* FIND TAKE PROFITS *************
    profits = findTakeProfits(string)
    print(profits)


## Check if post is a Entry point or not
async def isEntry(PostData):
    try:
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
            entry_price_value = float(re.findall(r"\d+\.?\d+", entry_price)[0])
            entry_target = await sync_to_async(EntryTarget.objects.get)(
                post__message_id=PostData.reply_to_msg_id, index=entry_index
            )

            if entry_target:
                # bigger_number = max(entry_price_value, float(entry_target.value))
                # smaller_number = min(entry_price_value, float(entry_target.value))

                # error = (100 * (1 - (smaller_number / bigger_number))) > 1
                # if error:
                #     return False
                # else:
                entry_target.active = True
                entry_target.date = PostData.date
                # entry_target.date = period
                await sync_to_async(entry_target.save)()
                return True

        return False
    except:
        error_msg.append(model_to_dict(PostData))
        return False

    
## Check if post is a Stoploss point or not
async def isStopLoss(post):
    
    try:
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

            
        if check or check1:
            
            predict = await sync_to_async(Predict.objects.get)(
                post__message_id=post.reply_to_msg_id
            )
           
            predict_type = await sync_to_async(lambda: predict.status.type)()
            if predict_type > 0:
                status_value = await sync_to_async(PostStatus.objects.get)(name="FAILED WITH PROFIT", type=predict_type)
            else:
                status_value = await sync_to_async(PostStatus.objects.get)(name="FAILED")
            
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
    except:
        # error_msg.append(model_to_dict(post))
        return False


## Check if post is a Take-Profit point or not
async def isTakeProfit(PostData):
    if PostData is None or PostData.reply_to_msg_id is None:
        return None
    
    try:

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
            status_value = await sync_to_async(PostStatus.objects.get)(name="SUCCESS", type=tp_index+1)
        
            if tp_target:

                tp_target.active = True
                tp_target.date = PostData.date
                tp_target.period = returnSearchValue(
                    re.search(r"Period: (.+)", PostData.message)
                )

                predict.profit = tp_target.profit
                predict.status = status_value
                await sync_to_async(tp_target.save)()
                await sync_to_async(predict.save)()
                return True

        return False
    except:
        # error_msg.append(model_to_dict(PostData))
        return False

## Check if post is a Cancel predict or not
async def isCancel(post):
    if post is None or post.reply_to_msg_id is None:
        return False
    
    try:
        cancel_before_patterns = [
            r"Cancelled\s",
            r"achieved\s",
            r"entering\s",
        ]
        manually_cancel_patterns = [
            r"Cancelled\s",
            r"achieved\s",
            r"entering\s",
        ]
        cancel_pattern =[
            r"کنسل\s"
        ]

        check = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in cancel_before_patterns)
        check1 = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in manually_cancel_patterns)
        check2 = all(re.search(pattern, post.message, re.IGNORECASE) for pattern in cancel_pattern)
        if check or check1 or check2:
            
            predict = await sync_to_async(Predict.objects.get)(
                post__message_id=post.reply_to_msg_id
            )
           
            status_value = await sync_to_async(PostStatus.objects.get)(name="CANCELED")
       
            predict.status = status_value
      
            await sync_to_async(predict.save)()
            return True
            
        else:
            return False
        
    except:
        # error_msg.append(model_to_dict(post))
        return False


## Check if post is a AllEntryPrice point or not
async def isAllEntryPrice(post):
    if post is None or post.reply_to_msg_id is None:
        return False
    try:
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
        return check
    except:
        error_msg.append(model_to_dict(post))
        return False

## Check if post is a AllProfit point or not
async def isAllProfitReached(post):
    if post is None or post.reply_to_msg_id is None:
        return False   
    
    try:

    
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


            status_value = await sync_to_async(PostStatus.objects.get)(name="FULLTARGET")
            predict_value = await sync_to_async(Predict.objects.get)(
                post__message_id=post.reply_to_msg_id
            )

            predict_value.status = status_value
            await sync_to_async(predict_value.save)()
            return True
        else:
                return False
    except:
        # error_msg.append(model_to_dict(post))
        return False

## Find important parts of a predict message such as symbol or entry point
async def predictParts(string, post):
    if string is None or post is None:
        return None
    
    try:
        settings = await sync_to_async(SettingConfig.objects.get)(id=1)
        
        # symbol
        symbol_value = await findSymbol(string)

        # market
        market_value= await findMarket(string)
        isSpot = market_value.name == "SPOT"

        # position, leverage, marginMode
        position_value = None
        leverage_value = None
        marginMode_value = None
        if not isSpot:
            position_value = await findPosition(string)
            marginMode_value, leverage_value = await findLeverage(string)
        else:
            position_value= await sync_to_async(PositionSide.objects.get)(name="BUY")
        
        # stopLoss
        stopLoss_value = findStopLoss(string)

        # entry targets
        entry_targets_value = findEntryTargets(string)

        # status    
        status_value = await sync_to_async(PostStatus.objects.get)(name="PENDING")

        # take_profit targets
        take_profit_targets_value = findTakeProfits(string)

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

        

        await sync_to_async(newPredict.save)()
        return newPredict

    except:
        # error_msg.append(model_to_dict(post))

        return False
        
## Find message type and save to DB
async def extract_data_from_message(message):
    if isinstance(message, Message):
        is_predict_msg = isPredictMsg(message.message)
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
            await predictParts(message.message, post)
        # entry msg
        elif await isEntry(post):
            pass
        # # take profit msg
        elif await isTakeProfit(post):
            pass
        # # stop loss msg
        elif await isStopLoss(post):
            pass 
        # # cancel msg
        elif await isCancel(post):
            pass
        # All Profit msg
        elif await isAllProfitReached(post):
            pass
        # # All EntryPrice msg
        elif await isAllEntryPrice(post):
            pass

        return PostData
    else:
        return None


## Get channel history
async def main():
    client = await TelegramClient(username, api_id, api_hash).start()
    peer_channel =  PeerChannel(int(config["CHANNEL_FEYZ"]))
    feyzian_channel = await client.get_entity(peer_channel)

    offset_id = 0
    limit = 100
    all_messages = []
    total_messages = 0
    total_count_limit = 0
    end_date = datetime(2024, 5, 20, tzinfo=timezone.utc)

    shouldStop = False
    while not shouldStop:
        print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
        history = await  client(
        GetHistoryRequest(
            peer=feyzian_channel,
            offset_id=offset_id,
            offset_date=None,
            # offset_date=start_date,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0,
        )
    )

        if not history.messages:
            break
        messages = history.messages
        for message in tqdm(messages):
            message_date = message.date.replace(tzinfo=timezone.utc)
            if message_date < end_date:
                shouldStop = True
                break
            all_messages.append(message)

        offset_id = messages[len(messages) - 1].id
        total_messages = len(all_messages)
        if total_count_limit != 0 and total_messages >= total_count_limit:
            break

    await client.disconnect()

    for msg in reversed(all_messages):
        await extract_data_from_message(msg)

if __name__ == "__main__":
    asyncio.run(main())


    
folder_name = "all_json"

# print(error_msg)
convertToJsonFile(error_msg, "error_msg", folder_name)