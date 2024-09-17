from bingx.api import BingxAPI
from dotenv import dotenv_values

# ****************************************************************************************************************************

_config = dotenv_values(".env")

class BingXApiClass:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = BingxAPI(_config["API_KEY"], _config["SECRET_KEY"], timestamp="local")
        return cls._instance
