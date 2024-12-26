from Shared.helpers import calStoploss


def updateTakeProfitByEntry(entry_price:list[float, str], leverage:int, isShort:str, max_percent_stoploss:int)-> list[float]:
    
    first_entry = entry_price[0]

    return [calStoploss(entry=first_entry, leverage=leverage, isShort= isShort, max_percent_stoploss=max_percent_stoploss)]
   

