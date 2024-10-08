
PROFIT_ERROR = 'Error in position or take-profit'
ENTRY_ERROR = 'Error in position or entry'
STOPLOSS_ERROR = 'Error in position or stoploss'

# will find error in take-profits(TP), entries, stoploss or position
# in LONG position, if first TP is smaller than second TP, it should return error
# in LONG position, if first entry is bigger than second entry, it should return error
def findError(position: str, tps: list[float], entries: list[float], stoploss: float)-> tuple[bool, str]:
    if position == "LONG":
        prev_tp = tps[0]
        for i in range(1, len(tps)):
            # error
            if tps[i] < prev_tp:
                return True, PROFIT_ERROR
            prev_tp = tps[i]
            
        prev_en = entries[0]
        for i in range(1, len(entries)):
            # error
            if entries[i] > prev_en:
                return True, ENTRY_ERROR
            prev_en = entries[i]
            
            
        for i in range(len(entries)):  
            # error
            if stoploss > entries[i]:
                return True, STOPLOSS_ERROR
            

    elif position == "SHORT":
        prev_tp = tps[0]
        for i in range(1, len(tps)):
            # error
            if tps[i] > prev_tp:
                return True, PROFIT_ERROR
            prev_tp = tps[i]
            
        prev_en = entries[0]
        for i in range(1, len(entries)):
            # error
            if entries[i] < prev_en:
                return True, ENTRY_ERROR
            prev_en = entries[i]
            
            
        for i in range(len(entries)):  
            # error
            if stoploss < entries[i]:
                return True, STOPLOSS_ERROR
            
    # spot
    elif position == "BUY":
        pass


    return False, ''
   
            
