
from operator import itemgetter
from Shared.helpers import convertToJsonFile

async def saveOHLC_toJson(symbolName, path, data):
    unique_data = {}
    for item in data:
        if item['time'] not in unique_data:
            unique_data[item['time']] = item

    # Convert the dictionary back to a list
    unique_list = list(unique_data.values())
    
    # Sort the unique data by the "time" key
    unique_list.sort(key=itemgetter('time'))
    
    convertToJsonFile(unique_list, symbolName, path) 