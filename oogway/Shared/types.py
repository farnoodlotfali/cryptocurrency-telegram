from typing import Literal, Optional, List, Optional, TypedDict, Any
from Shared.Constant import MarketValues

MarketName = Literal[MarketValues.FUTURES, MarketValues.SPOT]

class Stat(TypedDict):
    tps: List[Any]                  
    entry_reached: List[Any]       
    stop_loss_reached: Optional[Any] 
    break_reason: Optional[Any]  