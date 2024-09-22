from Shared.helpers import convertToJsonFile, load_json
from typing import Optional

_error_path_folder = '../errors-in-channel'

def errorSaver(data, channel_name: Optional[str] = None):
    filename = channel_name if channel_name else "general"
    loaded_data = load_json(f"{_error_path_folder}/{filename}.json")

    loaded_data.append(data)

    convertToJsonFile(loaded_data, filename, _error_path_folder) 