from abc import ABC, abstractmethod
from typing import Optional
from PostAnalyzer.models import (
    Market,
    Post,
    Predict,
    Symbol,
    PositionSide,
    MarginMode
)


class AbsChannel(ABC):
    
    # determine if a message is a predict message or not
    @abstractmethod
    def isPredictMsg(self, msg)-> bool:
        pass
    
    # find symbol
    @abstractmethod
    async def findSymbol(self, msg)-> Optional[Symbol]:
        pass
    
    # find market
    @abstractmethod
    async def findMarket(self, msg)-> Optional[Market]:
        pass
    
    # find position side
    @abstractmethod
    async def findPosition(self, msg)-> Optional[PositionSide]:
        pass
    
    # find leverage and margin mode
    @abstractmethod
    async def findLeverageAndMarginMode(self, msg)-> tuple[Optional[MarginMode], Optional[int]]:
        pass
    
    # find stopLoss
    @abstractmethod
    async def findStopLoss(self, msg)-> Optional[float]:
        pass
    
    # find entry targets
    @abstractmethod
    def findEntryTargets(self, msg)-> Optional[list[float]]:
        pass
    
    # find takeP profits
    @abstractmethod
    def findTakeProfits(self, msg)-> Optional[list[float]]:
        pass
    
    
    # find important parts of a predict message such as symbol or entry point
    @abstractmethod
    async def predictParts(self, string, post: Post)-> Optional[Predict]:
        pass
    
    # 
    @abstractmethod
    async def extract_data_from_message(self, msg):
        pass
