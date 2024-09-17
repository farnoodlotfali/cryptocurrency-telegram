def findError(position, tps, entries, stoploss):
    if position == "LONG":
        prev_tp = tps[0]
        for i in range(1, len(tps)):
            # error
            if tps[i] < prev_tp:
                return True
            prev_tp = tps[i]
            
        prev_en = entries[0]
        for i in range(1, len(entries)):
            # error
            if entries[i] > prev_en:
                return True
            prev_en = entries[i]
            
            
        for i in range(len(entries)):  
            # error
            if stoploss > entries[i]:
                return True
            

    elif position == "SHORT":
        prev_tp = tps[0]
        for i in range(1, len(tps)):
            # error
            if tps[i] > prev_tp:
                return True
            prev_tp = tps[i]
            
        prev_en = entries[0]
        for i in range(1, len(entries)):
            # error
            if entries[i] < prev_en:
                return True
            prev_en = entries[i]
            
            
        for i in range(len(entries)):  
            # error
            if stoploss < entries[i]:
                return True
            

    return False
   
            
