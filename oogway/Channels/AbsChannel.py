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
from Shared.findError import findError

# ****************************************************************************************************************************


class AbsChannel(ABC):
    
    # determine if a message is a predict message or not
    @abstractmethod
    def isPredictMsg(self, msg:str)-> bool:
        pass
    
    # find symbol
    @abstractmethod
    async def findSymbol(self, msg:str)-> Optional[Symbol]:
        pass
    
    # find market
    @abstractmethod
    async def findMarket(self, msg:str)-> Optional[Market]:
        pass
    
    # find position side
    @abstractmethod
    async def findPosition(self, msg:str)-> Optional[PositionSide]:
        pass
    
    # find leverage and margin mode
    @abstractmethod
    async def findLeverageAndMarginMode(self, msg:str)-> tuple[Optional[MarginMode], Optional[int]]:
        pass
    
    # find stopLoss
    @abstractmethod
    async def findStopLoss(self, msg:str)-> Optional[float]:
        pass
    
    # find entry targets
    @abstractmethod
    def findEntryTargets(self, msg:str)-> Optional[list[float]]:
        pass
    
    # find takeP profits
    @abstractmethod
    def findTakeProfits(self, msg:str)-> Optional[list[float]]:
        pass
    
    
    # find important parts of a predict message such as symbol or entry point
    @abstractmethod
    async def predictParts(self, string, post: Post)-> Optional[Predict]:
        pass 
    
    async def test(self, msg:str, showPrint:Optional[bool] = False)-> tuple[bool, str]:
        try:
            isPredict = self.isPredictMsg(msg)
            if not isPredict:
                raise Exception("Sorry, this msg is not Predict Message")

            # # ************* FIND SYMBOL *************
            symbol = await self.findSymbol(msg)
            if not symbol:
                raise Exception("Sorry, cannot find Symbol")


            # # ************* FIND MARKET *************
            market = await self.findMarket(msg)
            if not market:
                raise Exception("Sorry, cannot find Market")

            if market.name != "SPOT":
                # ************* FIND POSITION *************
                position = await self.findPosition(msg)
                if not position:
                    raise Exception("Sorry, cannot find Position")

                # ************* FIND LEVERAGE *************
                marginMode, leverage = await self.findLeverageAndMarginMode(msg)
                
                if not marginMode:
                    raise Exception("Sorry, cannot find MarginMode")
                if not leverage:
                    raise Exception("Sorry, cannot find Leverage")


            # # ************* FIND STOP LOSS *************
            stopLoss = self.findStopLoss(msg)
            if not stopLoss:
                raise Exception("Sorry, cannot find StopLoss")

            # # ************* FIND ENTRY TARGETS *************
            entries = self.findEntryTargets(msg)
            if not entries:
                raise Exception("Sorry, cannot find Entries")
            
            # # ************* FIND TAKE PROFITS *************
            profits = self.findTakeProfits(msg)
            if not profits:
                raise Exception("Sorry, cannot find Profits")
            
            is_error, is_error_message = findError(position.name, profits, entries, stopLoss)
            if is_error:
                raise Exception(is_error_message)

            
        except Exception as e:
            if showPrint: 
                print(e)
            return False, str(e)

        if showPrint: 
            print(f'isPredict: {isPredict}\nsymbol: {symbol.name}\nmarket: {market.name}')
            if market.name != "SPOT":
                print(f'position: {position.name}\nmarginMode: {marginMode.name}\nleverage: {leverage}')
            print(f'stopLoss: {stopLoss}\nentries: {entries}\nprofits: {profits}')
        

        return True, ''
    
    @abstractmethod
    async def extract_data_from_message(self, msg:str):
        pass
