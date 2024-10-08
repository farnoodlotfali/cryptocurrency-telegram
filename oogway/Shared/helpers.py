
import json
from datetime import datetime,timedelta
from typing import Match
import os
from IPython.display import HTML, display

def returnSearchValue(val: Match[str]):
    return val.group(1) if val else None
 

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
        
# convert to json file
def convertToJsonFile(data, name, folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(f"./{folder_name}/{name}.json", "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, cls=DateTimeEncoder, ensure_ascii=False)

# load json file
def load_json(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []
    return data

# compering 2 number return bigger and smaller number
def compare_two_numbers(num1, num2):
    if num1 > num2:
        return num1, num2
    else:
        return  num2, num1

# find duration between two timestamps
def subtractTime(date1, date2):
    big,small = compare_two_numbers(date1, date2)
    
    # Calculate the difference in milliseconds
    time_difference_ms = big - small

    # Convert the difference to seconds
    time_difference_s = time_difference_ms / 1000

    # Create a timedelta object from the difference in seconds
    time_difference_td = timedelta(seconds=time_difference_s)

    # Extract days, hours, and minutes from the timedelta object
    days = time_difference_td.days
    hours, remainder = divmod(time_difference_td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    result = f"{days} Days {hours} Hours {minutes} Minutes {seconds} Seconds"
    return result

# convert timestamp to datetime
def convertTimestampToDateTime(time):
    return datetime.fromtimestamp(time / 1000).strftime('%B %d, %Y, %I:%M %p').lower().replace('pm', 'p.m').replace('am', 'a.m')

# Function to print colored text
def print_colored(text, color):
    display(HTML(f"<p style='color:{color};'>{text}</p>"))

def getNowTimestamp():
    now = datetime.now().timestamp()
    return int(now * 1000)


# load data of tohlcv / Timestamp, Open, High, Low, Close, Volume
def load_historic_tohlcv_json(symbolName:str)-> list[any]:
    return load_json(f"./../historic-json/{symbolName}.json")

# save data of tohlcv to json / Timestamp, Open, High, Low, Close, Volume
def save_historic_tohlcv_json(symbolName, data):
    unique_data = {item[0]: item for item in data}

    # Convert the dictionary back to a list of lists
    unique_data_list = list(unique_data.values())

    # Sort by the first element (timestamp) if needed
    unique_data_list.sort(key=lambda x: x[0])
    
    convertToJsonFile(unique_data_list, symbolName, './../historic-json') 

