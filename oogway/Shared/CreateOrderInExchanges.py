from Shared.Exchange import exchange
from Shared.helpers import find_nearest_number_for_coienex_leverage
from Shared.Constant import PositionSideValues, OrderSide, OrderType, MarginModeValues

def createOrderInCoinEx(symbol:str, entry:float,
                                    leverage:int, side:OrderSide, type:OrderType, 
                                    stoploss:float, takeProfit:float, position:PositionSideValues,
                                    max_entry_money:float):

    exchange.set_leverage(
        leverage=find_nearest_number_for_coienex_leverage(leverage),
        symbol=symbol,
        params={
            'marginMode': MarginModeValues.ISOLATED.value
        }
    )

    size_volume = max_entry_money / float(entry)
    
    # set order in exchange
    print(entry, size_volume, "tp: ",takeProfit,"sl: ", stoploss, position)
    order_data = exchange.create_order(
        symbol=symbol,
        type=type,
        side=side,
        amount=size_volume,
        price=entry,
        params={
            'positionSide': position,
            'takeProfit': {
                "type": "TAKE_PROFIT_MARKET",
                "quantity": size_volume,
                "stopPrice": takeProfit,
                "price": takeProfit,
                "workingType": "MARK_PRICE"
            },
            'stopLoss': {
                "type": "TAKE_PROFIT_MARKET",
                "quantity": size_volume,
                "stopPrice": stoploss,
                "price": stoploss,
                "workingType": "MARK_PRICE"
            }
        }
    )
    print(order_data)
    return order_data['id']


def createOrderInXt(symbol:str, entry:float,
                                    leverage:int, side:OrderSide, type:OrderType, 
                                    stoploss:float, takeProfit:float, position:PositionSideValues,
                                    max_entry_money:float):
    
    exchange.set_leverage(leverage=leverage, symbol=symbol ,params={
                    'positionSide': position
                })
    

    amount = 4

    order_data = exchange.create_order(symbol, type, side, amount, entry, {})    
    print(order_data)
    return order_data['id']
