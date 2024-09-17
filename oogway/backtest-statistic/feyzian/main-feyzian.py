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
from datetime import datetime,timedelta
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

peer_channel = PeerChannel(int(config["CHANNEL_FEYZ"]))
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
    # Calculate the difference in milliseconds
    time_difference_ms = date1 - date2

    # Convert the difference to seconds
    time_difference_s = time_difference_ms / 1000

    # Create a timedelta object from the difference in seconds
    time_difference_td = timedelta(seconds=time_difference_s)

    # Extract days, hours, and minutes from the timedelta object
    days = time_difference_td.days
    hours, remainder = divmod(time_difference_td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    result = f"{days} Days {hours} Hours {minutes} Minutes"
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
def remove(folder):
    
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
        r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT",
        r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)",
        r"Entry Targets:([\s\S]+?)Take-Profit",
        r"Market:\s*([A-Z]+)",
        r"(StopLoss|Description):\s*([\d.]|\w+)",
    ]

    # Check if all patterns have a value
    return all(re.search(pattern, msg, re.IGNORECASE) for pattern in patterns)


# find important parts of a predict message such as symbol or entry point
def predictParts(string):
    if string is None:
        return None

    # print(string)
    symbol_match = re.search(r"Symbol:\s*#?([A-Z0-9]+)[/\s]?USDT", string, re.IGNORECASE)
    position_match =  re.search(r"Position:\s*([A-Z]+)", string, re.IGNORECASE)
    leverage_match = re.search(r"Leverage:\s*(Isolated|Cross)\s*(\d+x)", string, re.IGNORECASE)
    if leverage_match:
        marginMode = returnSearchValue(leverage_match).upper() 
        leverage_value = int(leverage_match.group(2).lower().replace("x",""))    
    else:
        marginMode = None
        leverage_value = None
    market_match = re.search(r"Market:\s*([A-Z]+)", string, re.IGNORECASE)
    stopLoss_match = re.search(r"StopLoss:\s*([\d.]+)", string)

    # Extracting values from entry targets
    entry_targets_match = returnSearchValue(re.search(r"Entry Targets:([\s\S]+?)Take-Profit", string, re.IGNORECASE))
    entry_values = [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", entry_targets_match))  if i % 2 == 1]

    take_profit_targets_match =returnSearchValue(re.search(r"Take-Profit Targets:([\s\S]+?)(StopLoss|Description)", string, re.IGNORECASE))
    profit_values = [float(x.strip()) for i, x in enumerate(re.findall(r"(\d+\.\d+|\d+)", take_profit_targets_match)) if i % 2 == 1]

    # Creating a dictionary
    data = {
        "Symbol": returnSearchValue(symbol_match),
        "Position": returnSearchValue(position_match),
        "Market": returnSearchValue(market_match),
        "Leverage": leverage_value ,
        "StopLoss": returnSearchValue(stopLoss_match),
        "Margin_mode": marginMode,
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
        "Profit": 0,
        "Status": "pending",
    }

    return data


# check if str(msg) is a Entry point or not
def isEntry(msg, value, symbol):
    entry_price = returnSearchValue(
        re.search(r"Entry Price: (.+)", msg)
    )

    entry_index = returnSearchValue(re.search(r"Entry(.+)", msg))

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
    check = all(re.search(pattern, msg) for pattern in patterns)

    # Check if the words "achieved" and "all" are not present
    words_absent = not re.search(r"achieved", msg, re.IGNORECASE) and not re.search(r"\ball\b", msg, re.IGNORECASE)
    
    # for control "average entry".
    # sometimes entry_price is different to value. so we should find difference, then calculate error

    entry_price_value = re.findall(r"\d+\.\d+", entry_price)
    if entry_price and check and words_absent and len(entry_price_value) > 0: 
        entry_price_value = float(entry_price_value[0])

        bigger_number = max(entry_price_value, float(value))
        smaller_number = min(entry_price_value, float(value))

        error = (100 * (1 - (smaller_number / bigger_number))) > 1
        if error:
            return False
        else:
            
            return True

    return False


# check if str(msg) is a Stoploss point or not
def isStopLoss(msg):
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

    check = all(re.search(pattern, msg, re.IGNORECASE) for pattern in failed_with_profit_patterns)
    check1 = all(re.search(pattern, msg, re.IGNORECASE) for pattern in failed_patterns)

    return check1 or check
     

# check if str(msg) is a Take-Profit point or not
def isTakeProfit(msg, symbol, index):
    patterns = [
        r"Take-Profit(.+)",
        r"Profit(.+)",
        r"Period(.+)",
    ]

    # Check if all patterns have a value
    return all(re.search(pattern, msg) for pattern in patterns)


def extract_data_from_message(message):
    if isinstance(message, Message):
        is_predict_msg = isPredictMsg(message.message)
        
        data = {
            "id": message.id,
            "date": int(message.date.timestamp() * 1000),
            "reply_to_msg_id": message.reply_to.reply_to_msg_id
            if message.reply_to
            else None,
            "message": message.message,
            "edit_date": int(message.edit_date.timestamp() * 1000) if message.edit_date else None ,
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
    for message in tqdm(messages):
        # to control msg date time
        message_date = message.date.replace(tzinfo=timezone.utc)
        # end_date = datetime(2023, 10, 19, tzinfo=timezone.utc)
        end_date = datetime(2024, 5, 20, tzinfo=timezone.utc)
        if message_date < end_date:
            shouldStop = True
            break

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
total_messages = all_messages.copy()
total_messages.sort(
    key=lambda x: x["reply_to_msg_id"]
    if x["reply_to_msg_id"] is not None
    else float("inf")
)
groups = groupby(total_messages, key=lambda x: x["reply_to_msg_id"])

grouped_data = {str(key): list(group) for key, group in groups}
del grouped_data["None"]

# ****************************************************************************************************************************
for msg in predict_messages:
    if not f'{msg["id"]}' in grouped_data:
        continue

    entries = msg["predict"]["Entry Targets"]
    take_profits = msg["predict"]["Take-Profit Targets"]
    symbol = msg["predict"]["Symbol"]

    all_predicts = grouped_data[f'{msg["id"]}'].copy()
    isEntryActive = False

    for i, value in enumerate(all_predicts):
        if isStopLoss(value["message"]):
            msg["predict"]["Status"] = "failed"
            del all_predicts[i]
            break

    for item in entries:
        for i, value in enumerate(all_predicts):
            if isEntry(value["message"], item["value"], symbol):
                item["active"] = True
                item["date"] = value["date"]
                item["Period"] = subtractTime(msg["date"], value["date"])
                del all_predicts[i]
                isEntryActive = True
                break

    # there is no take-profit if none of entry points is active
    # if isEntryActive:
    for j, item in enumerate(take_profits):
        for i, value in enumerate(all_predicts):
            if isTakeProfit(value["message"], symbol, j + 1):
                item["active"] = True
                item["date"] = value["date"]
                item["Period"] = returnSearchValue(
                    re.search(r"Period: (.+)", value["message"])
                )
                del all_predicts[i]
                break


# ****************************************************************************************************************************
# def contains_persian(text):
#     persian_regex = re.compile('[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')
#     return bool(persian_regex.search(text))
# grouped_data_with_control = grouped_data.copy()
# grouped_data_with_control["None"] =  [item for item in grouped_data_with_control["None"]  if not item["is_predict_msg"] and item["media"] is None and not contains_persian(item["message"])]



# ****************************************************************************************************************************

# save date to csv file
# folder_name = "all_csv"
# remove(folder_name)
# convertToCSVFile(all_messages, "channel_messages", folder_name)
# convertToCSVFile(predict_messages, "predict_messages", folder_name)

# ****************************************************************************************************************************
# save date to json file
folder_name = "all_json"
convertToJsonFile(all_messages, "channel_messages", folder_name)
convertToJsonFile(grouped_data, "grouped_messages", folder_name)
# convertToJsonFile(grouped_data_with_control["None"], "control", folder_name)
convertToJsonFile(predict_messages, "predict_messages", folder_name)
