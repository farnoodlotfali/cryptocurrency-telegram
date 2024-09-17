from dotenv import dotenv_values
from typing import Literal


# ****************************************************************************************************************************


_config = dotenv_values(".env")


def SymbolConverter(symbol:str, transactions: Literal['FUTURES', 'SPOT'] = 'FUTURES'):
    exchange = _config["EXCHANGE_ID"]

    if exchange == 'bingx':
        # example => symbol = BTC/USDT => return => BTC/USDT:USDT
        if transactions == 'FUTURES':
            return f'{symbol.replace("-", "/")}:USDT'
        return symbol.replace("-", "/")

        


