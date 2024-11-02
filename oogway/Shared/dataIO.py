from Shared.Exchange import exchange
from Shared.types import MarketName
from Shared.helpers import load_json, rootConvertToJsonFile
import os


_path_folder = os.path.join(os.path.dirname(__file__), "../historic-json")

# example ==> BTC-SPOT-bingx
def ohlcv_name_file(symbolName:str, marketName:MarketName)-> str:
    return f'{symbolName.replace('/','-').split(':')[0]}-{marketName}-{exchange.id}'

# load data of tohlcv / Timestamp, Open, High, Low, Close, Volume
def load_historic_tohlcv_json(symbolName:str, marketName:MarketName)-> list[any]:
    return load_json(f"{_path_folder}/{ohlcv_name_file(symbolName, marketName)}.json")

# save data of tohlcv to json / Timestamp, Open, High, Low, Close, Volume
def save_historic_tohlcv_json(symbolName:str, marketName:MarketName, data):
    unique_data = {item[0]: item for item in data}

    # Convert the dictionary back to a list of lists
    unique_data_list = list(unique_data.values())

    # Sort by the first element (timestamp) if needed
    unique_data_list.sort(key=lambda x: x[0])

    symbolName = symbolName.replace('/','-').split(':')[0]
    
    rootConvertToJsonFile(unique_data_list, ohlcv_name_file(symbolName, marketName), _path_folder) 

