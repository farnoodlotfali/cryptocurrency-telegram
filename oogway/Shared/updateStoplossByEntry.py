from Shared.helpers import calStoploss


def updateStoplossByEntry(entry_price:list[float, str], leverage:int, isShort:str, max_percent_stoploss:int)-> float:
    
    first_entry = entry_price[0]

    return calStoploss(entry=first_entry, leverage=leverage, isShort=not isShort, max_percent_stoploss=max_percent_stoploss)
   

