from Shared.helpers import rootConvertToJsonFile, load_json
from typing import Optional
import os

_error_path_folder = os.path.join(os.path.dirname(__file__), "../errors-in-channel")

def errorSaver(data, channel_name: Optional[str] = None):
    filename = channel_name if channel_name else "general"
    loaded_data = load_json(f"{_error_path_folder}/{filename}.json")
    loaded_data.append(data)

    rootConvertToJsonFile(loaded_data, filename, _error_path_folder) 