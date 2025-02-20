
import json
from datetime import datetime,timedelta
from typing import Match, Optional
import os
from IPython.display import HTML, display
import pandas as pd


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
    

def rootConvertToJsonFile(data, name, folder_name):
    # # Ensure the folder exists
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
   
    # Use os.path.join to construct the full path
    file_path = os.path.join(folder_name, f"{name}.json")
    
    with open(file_path, "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, cls=DateTimeEncoder, ensure_ascii=False, skipkeys=True)

        
# convert to json file
def convertToJsonFile(data, name, folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    with open(f"./{folder_name}/{name}.json", "w", encoding="utf-8") as outfile:
        json.dump(data, outfile, cls=DateTimeEncoder, ensure_ascii=False)

# load json file
def load_json(filename):
    try:
        with open(filename, 'r', encoding="utf-8") as file:
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


def addDaysToMilliTimeStamp(time:int, days:int)->int:

    time = time / 1000
   
    original_datetime = datetime.fromtimestamp(time)

    new_datetime = original_datetime + timedelta(days=days)

    new_time = int(new_datetime.timestamp() * 1000)
    return new_time


def convertDateToMilliTimeStamp(year:int, month:int, day:int, hour:int, minute:int, second:int=0)-> int:
    dt = datetime(year, month, day, hour, minute, second)

    return int(dt.timestamp())*1000



def zero_hours_minutes_seconds(timestamp_ms):
    # Convert to datetime object
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    
    # Set minutes and seconds to zero
    dt_zeroed = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Convert back to timestamp in milliseconds
    return int(dt_zeroed.timestamp() * 1000)


def findProfit(first_value:float, second_value:float, leverage:int, percent:bool = True)-> float:
    profit = round(abs(((second_value/first_value)-1)*100*leverage), 5)

    if percent:
        return profit

    return profit/100




def find_nearest_number_for_coienex_leverage(target):
    arr = [1, 2, 3, 5, 8, 10, 15, 20, 30, 50, 100]
    return min(arr, key=lambda x: abs(x - target))



def calStoploss(entry:float, leverage:int, isShort:bool, max_percent_stoploss:float):
    return entry*(1+(max_percent_stoploss/(100*leverage*(1 if isShort else -1)))) 
