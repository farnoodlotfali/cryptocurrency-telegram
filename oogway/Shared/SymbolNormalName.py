

from dotenv import dotenv_values
from typing import Literal


# ****************************************************************************************************************************


_config = dotenv_values(".env")


def SymbolNormalName(symbol:str, transactions: Literal['FUTURES', 'SPOT'] = 'FUTURES'):
    exchange = _config["EXCHANGE_ID"]

    if exchange == 'bingx':
        # example => symbol =  BTC/USDT:USDT => return => BTC-USDT
        if transactions == 'FUTURES':
            return symbol.split(':')[0].replace('/', '-')
    