from telethon.sync import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
import json
from datetime import date, datetime, timezone
from tqdm import tqdm
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


# user_input_channel = input('enter entity(telegram URL or entity id):')

peer_channel = PeerChannel(int(config["CHANNEL_ALI_BEY"]))
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


# will find position type
def findPosition(msg):
    pos = None
    if "short" in msg.lower():
        pos = "SHORT"
    elif "long" in msg.lower():
        pos = "LONG"

    return pos


# will find market name
def findMarket(msg):
    market = None
    if "Futures Call".lower() in msg.lower():
        market = "FUTURES"
    elif "Spot".lower() in msg.lower():
        market = "SPOT"

    return market


# determine if a message is a predict message or not
def isPredictMsg(msg):
    patterns = [
        r"📌 #(.+)",
        r"Entry:(.+)",
        r"Leverage:(.+)",
        r"Stop : (.+)",
        r"TP:(.+)",
    ]

    # Check if all patterns have a value
    return all(re.search(pattern, msg) for pattern in patterns)


# find important parts of a predict message such as symbol or entry point
def predictParts(string):
    if string is None:
        return None

    symbol_match = re.search(r"📌 #(.+)", string)
    position_match = findPosition(string)
    leverage_match = re.search(r"Leverage: (.+)", string)
    market_match = findMarket(string)
    stopLoss_match = re.search(r"Stop : (.+)", string)

    # Extracting values from entry targets
    entry_targets_match = re.search(r"Entry:(.+?)\n\n", string, re.DOTALL)
    entry_values = (
        re.findall(r"\d+(?:\.\d+)?", entry_targets_match.group(1))
        if entry_targets_match
        else None
    )

    take_profit_targets_match = re.search(r"TP:(.+?)\n\n", string, re.DOTALL)
    profit_values = (
        re.findall(r"\d+(?:\.\d+)?", take_profit_targets_match.group(1))
        if take_profit_targets_match
        else None
    )

    # Creating a dictionary
    data = {
        "Symbol": returnSearchValue(symbol_match),
        "Position": position_match,
        "Market": market_match,
        "Leverage": returnSearchValue(leverage_match),
        "StopLoss": returnSearchValue(stopLoss_match),
        "Entry Targets": [
            {"index": i, "value": value, "active": False, "Period": None, "date": None}
            for i, value in enumerate(entry_values)
        ],
        "Take-Profit Targets": [
            {"index": i, "value": value, "active": False, "Period": None, "date": None}
            for i, value in enumerate(profit_values)
        ]
        if profit_values
        else None,
        "status": "pending",
    }

    return data


# check if str(msg) is a Take-Profit point or not
def isTakeProfit(msg, symbol, index):
    patterns = [
        rf"Full targets achieved Tp{index}(.+)",
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
            # "media": message.media.to_dict() if message.media else None,
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
    for message in tqdm(messages):
        # to control msg date time
        message_date = message.date.replace(tzinfo=timezone.utc)
        # end_date = datetime(2023, 10, 19, tzinfo=timezone.utc)
        end_date = datetime(2024, 5, 21, tzinfo=timezone.utc)
        if message_date < end_date:
            shouldStop = True
            break
        # print(message_date, end_date)

        # will download img and save it a folder called "hi"
        # client.download_media(message, "./"+"hi"+"/")
        message_data = extract_data_from_message(message)
        # print(message_data['message'] if message_data else None)

        # all_messages.append(message.to_dict())
        all_messages.append(message_data)

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
#     else float("-inf")
# )

# # Group the list by the "reply_to_msg_id" field
# grouped = groupby(total_messages, key=lambda x: x["reply_to_msg_id"])

# # Convert the grouped data to a JSON-serializable format
# grouped_data = [{str(key): list(group) for key, group in grouped}]
# del grouped_data["None"]
total_messages = all_messages.copy()
total_messages.sort(
    key=lambda x: x["reply_to_msg_id"]
    if x["reply_to_msg_id"] is not None
    else float("inf")
)
groups = groupby(total_messages, key=lambda x: x["reply_to_msg_id"])

grouped_data = {str(key): list(group) for key, group in groups}
# del grouped_data["None"]

# # ****************************************************************************************************************************
#  ali beyranvand does not sent entry msg
for msg in predict_messages:
    entries = msg["predict"]["Entry Targets"]
    take_profits = msg["predict"]["Take-Profit Targets"]
    symbol = msg["predict"]["Symbol"]
    if f'{msg["id"]}' in grouped_data:
        all_predicts = grouped_data[f'{msg["id"]}'].copy()
        isPredictActive = False
        for j, item in enumerate(take_profits):
            for i, value in enumerate(all_predicts):
                if isTakeProfit(value["message"], symbol, j + 1):
                    item["active"] = True
                    item["date"] = value["date"]
                    item["Period"] = subtractTime(msg["date"], value["date"])
                    del all_predicts[i]
                    isPredictActive = True
                    break

        if isPredictActive:
            for item in entries:
                item["active"] = True
                item["date"] = None
                item["Period"] = None

# # ****************************************************************************************************************************

# # save date to csv file
# folder_name = "all_csv"
# convertToCSVFile(all_messages, "channel_messages", folder_name)

# # ****************************************************************************************************************************

# # save date to json file
folder_name = "all_json"
convertToJsonFile(all_messages, "channel_messages", folder_name)
convertToJsonFile(grouped_data, "grouped_messages", folder_name)
convertToJsonFile(predict_messages, "predict_messages", folder_name)
