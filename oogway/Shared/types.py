from typing import Literal, Optional, List, Optional, TypedDict, Any
from Shared.Constant import MarketValues

MarketName = Literal[MarketValues.FUTURES, MarketValues.SPOT]

class Stat(TypedDict):
    tps: List[Any]                  
    entry_reached: List[Any]       
    stop_loss_reached: Optional[Any] 
    break_reason: Optional[Any]  


class PredictNoModel(TypedDict):
    id: int               
    tps: List[float]                  
    entries: List[float]       
    stop_loss: float
    symbol: str
    market: str
    position: str
    leverage: int
    margin_mode: str
    date: int
    
 