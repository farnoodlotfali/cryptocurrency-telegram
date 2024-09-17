from telethon.sync import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
import json
from datetime import date, datetime, timezone
import csv
import re
import os, shutil
from telethon.tl.types import Message, PeerChannel
from telethon.tl.types import InputChannel
from itertools import groupby
from datetime import datetime
from dotenv import dotenv_values

# ****************************************************************************************************************************

config = dotenv_values(".env")

api_id = config["api_id"]
api_hash = config["api_hash"]

username = config["username"]
client = TelegramClient(username, api_id, api_hash).start()
# client.download_profile_photo(username)
# messages = client.get_messages(username)

# user_input_channel = input('enter entity(telegram URL or entity id):')

peer_channel = PeerChannel(int(config["CHANNEL_TEST_RASTAD"]))
my_channel = client.get_entity(peer_channel)

offset_id = 0
limit = 100
all_messages = []
predict_messages = []
total_messages = 0
total_count_limit = 0


# some functions to parse json date
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        if isinstance(o, bytes):
            return list(o)

        if isinstance(o, str):
            return o  # Return Persian text as is without encoding

        return json.JSONEncoder.default(self, o)


def returnSearchValue(val):
    return val.group(1) if val else None


#  subtract Times
def subtractTime(date1, date2):
    # Convert the datetime strings to datetime objects
    datetime1 = datetime.fromisoformat(date1.strftime("%Y-%m-%d %H:%M:%S"))
    datetime2 = datetime.fromisoformat(date2.strftime("%Y-%m-%d %H:%M:%S"))

    # Calculate the difference between the datetime objects
    time_difference = datetime2 - datetime1

    # Extract the hours and minutes from the time difference
    hours = time_difference.seconds // 3600
    minutes = (time_difference.seconds // 60) % 60

    # Format the result
    result = f"{hours} Hours {minutes} Minutes"
    return result


# convert to json
def convertToJsonFile(data, name, folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(f"./{folder_name}/{name}.json", "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, cls=DateTimeEncoder, ensure_ascii=False)


# convert to csv
def convertToCSVFile(data, name, folder_name):
    all_keys = set().union(*(msg.keys() for msg in data))
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(
        f"./{folder_name}/{name}.csv", "w", encoding="utf-8-sig", newline=""
    ) as outfile1:
        writer = csv.DictWriter(outfile1, fieldnames=all_keys)

        # Writing the column headers
        writer.writeheader()

        for item in data:
            writer.writerow(item)


# will remove all content in a folder
def remove():
    folder = "./hi"
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))


# determine if a message is a predict message or not
def isPredictMsg(msg):
    patterns = [
        r"Symbol: (.+)",
        # r"Position: (.+)",
        # r"Leverage: (.+)",
        r"Market: (.+)",
        r"StopLoss: (.+)",
    ]

    # Check if all patterns have a value
    return all(re.search(pattern, msg) for pattern in patterns)


# find important parts of a predict message such as symbol or entry point
def predictParts(string):
    if string is None:
        return None

    # print(string)
    symbol_match = re.search(r"Symbol: (.+)", string)
    position_match = re.search(r"Position: (.+)", string)
    leverage_match = re.search(r"Leverage: (.+)", string)
    market_match = re.search(r"Market: (.+)", string)
    stopLoss_match = re.search(r"StopLoss: (.+)", string)

    # Extracting values from entry targets
    entry_targets_match = re.search(r"Entry Targets:(.+?)\n\n", string, re.DOTALL)
    entry_values = (
        re.findall(r"\d+\.\d+", entry_targets_match.group(1))
        if entry_targets_match
        else None
    )

    take_profit_targets_match = re.search(
        r"Take-Profit Targets:(.+?)\n\n", string, re.DOTALL
    )
    profit_values = (
        re.findall(r"\d+\.\d+", take_profit_targets_match.group(1))
        if take_profit_targets_match
        else None
    )

    # Creating a dictionary
    data = {
        "Symbol": returnSearchValue(symbol_match),
        "Position": returnSearchValue(position_match),
        "Market": returnSearchValue(market_match),
        "Leverage": returnSearchValue(leverage_match),
        "StopLoss": returnSearchValue(stopLoss_match),
        "Entry Targets": [
            {"index": i, "value": value, "active": False, "Period": None, "date": None}
            for i, value in enumerate(entry_values)
        ]
        if entry_values
        else None,
        "Take-Profit Targets": [
            {"index": i, "value": value, "active": False, "Period": None, "date": None}
            for i, value in enumerate(profit_values)
        ]
        if profit_values
        else None,
        # "Entry Targets": {f"Target {i+1}": {"value": value, "active": False, "Period": None} for i, value in enumerate(entry_values)} if entry_values else None,
        # "Take-Profit Targets": {f"Target {i+1}": {"value": value, "active": False, "Period": None} for i, value in enumerate(profit_values)} if profit_values else None,
        "status": "pending",
    }

    return data


# check if str(msg) is a Entry point or not
def isEntry(msg, value, symbol):
    entry_price = returnSearchValue(re.search(r"Entry Price: (.+)", msg))
    # for control "average entry".
    # st entry_price is different to value. so we should find difference, then calculate error
    if entry_price:
        entry_price = float(re.findall(r"\d+\.\d+", entry_price)[0])
        bigger_number = max(entry_price, float(value))
        smaller_number = min(entry_price, float(value))

        error = 100 * (1 - (smaller_number / bigger_number)) > 1
        if error:
            return False
    else:
        return False

    patterns = [
        r"Entry(.+)",
        rf"{symbol}",
    ]

    # Check if all patterns have a value

    return all(re.search(pattern, msg) for pattern in patterns)


# check if str(msg) is a Stoploss point or not
def isStopLoss(msg):
    if "Stoploss".lower() in msg.lower() or "Stop loss".lower() in msg.lower():
        return True
    else:
        return False


# check if str(msg) is a Take-Profit point or not
def isTakeProfit(msg, symbol, index):
    patterns = [
        r"Take-Profit(.+)",
        r"Profit(.+)",
        rf"target {index}",
        rf"{symbol}",
    ]

    # Check if all patterns have a value
    return all(re.search(pattern, msg) for pattern in patterns)


def extract_data_from_message(message):
    if isinstance(message, Message):
        is_predict_msg = isPredictMsg(message.message)

        data = {
            "id": message.id,
            "date": message.date,
            "reply_to_msg_id": message.reply_to.reply_to_msg_id
            if message.reply_to
            else None,
            "message": message.message,
            "edit_date": message.edit_date,
            "is_predict_msg": is_predict_msg,
            "predict": predictParts(message.message) if is_predict_msg else None,
            "media": message.media.to_dict() if message.media else None,
        }
        if is_predict_msg:
            predict_messages.append(data)
        return data
    else:
        return None


# ****************************************************************************************************************************

shouldStop = False
while not shouldStop:
    print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
    history = client(
        GetHistoryRequest(
            peer=my_channel,
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
    for message in messages:
        # to control msg date time
        message_date = message.date.replace(tzinfo=timezone.utc)
        # end_date = datetime(2023, 10, 19, tzinfo=timezone.utc)
        end_date = datetime(2023, 10, 24, tzinfo=timezone.utc)
        if message_date < end_date:
            shouldStop = True
            break
        # print(message_date, end_date)

        # will download img and save it a folder called "hi"
        # client.download_media(message, "./"+"hi"+"/")
        # message_data = extract_data_from_message(message)
        # print(message_data['message'] if message_data else None)

        all_messages.append(message.to_dict())
        # all_messages.append(message_data)

    offset_id = messages[len(messages) - 1].id
    total_messages = len(all_messages)
    if total_count_limit != 0 and total_messages >= total_count_limit:
        break

# ****************************************************************************************************************************
# groupby data according to reply_to_msg_id
# total_messages = all_messages.copy()
# total_messages.sort(
#     key=lambda x: x["reply_to_msg_id"]
#     if x["reply_to_msg_id"] is not None
#     else float("inf")
# )
# groups = groupby(total_messages, key=lambda x: x["reply_to_msg_id"])

# grouped_data = {str(key): list(group) for key, group in groups}
# del grouped_data["None"]

# ****************************************************************************************************************************
# for msg in predict_messages:
#     if not f'{msg["id"]}' in grouped_data:
#         continue

#     entries = msg["predict"]["Entry Targets"]
#     take_profits = msg["predict"]["Take-Profit Targets"]
#     symbol = msg["predict"]["Symbol"]

#     all_predicts = grouped_data[f'{msg["id"]}'].copy()
#     isEntryActive = False

#     for i, value in enumerate(all_predicts):
#         if isStopLoss(value["message"]):
#             msg["predict"]["status"] = "failed"
#             del all_predicts[i]
#             break

#     for item in entries:
#         for i, value in enumerate(all_predicts):
#             if isEntry(value["message"], item["value"], symbol):
#                 item["active"] = True
#                 item["date"] = value["date"]
#                 item["Period"] = subtractTime(msg["date"], value["date"])
#                 del all_predicts[i]
#                 isEntryActive = True
#                 break

#     # there is no take-profit if none of entry points is active
#     if isEntryActive:
#         for j, item in enumerate(take_profits):
#             for i, value in enumerate(all_predicts):
#                 if isTakeProfit(value["message"], symbol, j + 1):
#                     item["active"] = True
#                     item["date"] = value["date"]
#                     item["Period"] = returnSearchValue(
#                         re.search(r"Period: (.+)", value["message"])
#                     )
#                     del all_predicts[i]
#                     break


# ****************************************************************************************************************************

# save date to csv file
folder_name = "all_csv"
convertToCSVFile(all_messages, "channel_messages", folder_name)

# ****************************************************************************************************************************

# save date to json file
folder_name = "all_json"
convertToJsonFile(all_messages, "channel_messages", folder_name)
# convertToJsonFile(grouped_data, "grouped_messages", folder_name)
# convertToJsonFile(predict_messages, "predict_messages", folder_name)
