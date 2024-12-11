from Shared.Constant import PositionSideValues, MAX_PROFIT_VALUE
from Shared.helpers import findProfit
from typing import Optional

PROFIT_ERROR = 'Error in position or take-profit'
ENTRY_ERROR = 'Error in position or entry'
STOPLOSS_ERROR = 'Error in position or stoploss'
PROFIT_MAX_PROFIT_VALUE_ERROR = 'Error, profit is bigger than MAX_PROFIT_VALUE'



# will find error in take-profits(TP), entries, stoploss or position
# in LONG position, if first TP is smaller than second TP, it should return error
# in LONG position, if first entry is bigger than second entry, it should return error
def findError(position: str, tps: list[float], entries: list[float], stoploss: float, leverage:Optional[int]= None, max_profit_percent:float= MAX_PROFIT_VALUE)-> tuple[bool, str]:
    
    # to remove 'market' entry
    entries = [item for item in entries if isinstance(item, (int, float))]
    
    if position == PositionSideValues.LONG.value:
        prev_tp = tps[0]
        for i in range(1, len(tps)):
            # error
            if tps[i] < prev_tp:
                return True, PROFIT_ERROR
            prev_tp = tps[i]
        
        if bool(entries):
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
                
            for et in entries:
                for tp in tps:
                    # error
                    if max_profit_percent < findProfit(et, tp, leverage):
                        return True, PROFIT_MAX_PROFIT_VALUE_ERROR


    elif position == PositionSideValues.SHORT.value:
        prev_tp = tps[0]
        for i in range(1, len(tps)):
            # error
            if tps[i] > prev_tp:
                return True, PROFIT_ERROR
            prev_tp = tps[i]

        if bool(entries):
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
                
            for et in entries:
                for tp in tps:
                    # error
                    if max_profit_percent < findProfit(et, tp, leverage):
                        return True, PROFIT_MAX_PROFIT_VALUE_ERROR
            
    # spot
    elif position == PositionSideValues.BUY.value:
        pass


    return False, ''
   
            
