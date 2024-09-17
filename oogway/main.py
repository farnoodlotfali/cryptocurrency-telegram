from bingx.api import BingxAPI
from dotenv import dotenv_values

# ****************************************************************************************************************************

config = dotenv_values(".env")

api_id = config["api_id"]

# Please note that it is smarter to use environment variables than hard coding your keys into your code.
API_KEY = config["API_KEY"]
SECRET_KEY = config["SECRET_KEY"]

# It is faster and more efficient to use local timestamps. If you are getting an error try using "server" timestamp.
bingx = BingxAPI(API_KEY, SECRET_KEY, timestamp="local")
order_data = bingx.open_limit_order(
    "BTC-USDT", "LONG", 30000.54, 0.0001, tp="30010.66", sl="29010"
)

# order_data1 = bingx.open_limit_order(
#     "BTC-USDT", "LONG", 30210.54, 0.0001, tp="34010.66", sl="29010"
# )
# print(order_data["orderId"])

cancel_data = bingx.cancel_order(
    "BTC-USDT", order_data["orderId"]
)
# print(cancel_data)

# order_data = bingx.get_levarage("BTC-USDT")
# print(order_data)

# order_data = bingx.set_levarage("BTC-USDT","LONG",9)
# print(order_data)

# order_data = bingx.get_all_contracts()
# print(order_data)

# order_data = bingx.get_latest_price("BTC-USDT")
# print(order_data)


# order_data = bingx.get_index_price("BTC-USDT")
# print(order_data)


# order_data = bingx.get_current_optimal_price("BTC-USDT")
# print(order_data)

# order_data = bingx.get_perpetual_balance()
# print(order_data)

# order_data = bingx.query_pending_orders()
# print(order_data)

# order_data = bingx.close_all_positions()
# print(order_data)

# order_data = bingx.cancel_all_orders_of_symbol()
# print(order_data)



# order_data = bingx.place_test_order(
#     trade_type="LIMIT",
#     pair="BTC-USDT",
#     desicion="BUY",
#     position_side="LONG",
#     price=32000,
#     volume=0.001,
#     stop_price="29000",
#     priceRate="0.5",
#     sl="29000",
#     tp="49000",
#     working_type="MARK_PRICE",
#     client_order_id="1",
#     time_in_force="GTC",
# )
# print(order_data)
