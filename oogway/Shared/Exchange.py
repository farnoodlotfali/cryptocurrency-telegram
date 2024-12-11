import ccxt
from dotenv import dotenv_values

_config = dotenv_values(".env")

# you can find other exchanges by running this:
# print(ccxt.exchanges)
# example print => ['ace', 'alpaca', 'binance', 'binancecoinm', 'bingx', ....... ]


_exchange_id = _config["EXCHANGE_ID"]
_exchange_class = getattr(ccxt, _exchange_id)
exchange: ccxt.Exchange = _exchange_class({
   'apiKey': _config["API_KEY"],
   'secret': _config["SECRET_KEY"],
   'enableRateLimit': True,
   # 'rateLimit': 3000, # 3 seconds
})