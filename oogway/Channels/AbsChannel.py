from abc import ABC, abstractmethod
from typing import Optional
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.sync import TelegramClient
from dotenv import dotenv_values
from telethon.tl.types import Message, PeerChannel
from datetime import datetime, timezone
from tqdm import tqdm
from django.forms.models import model_to_dict
from PostAnalyzer.models import (
    Market,
    Post,
    Predict,
    Symbol,
    PositionSide,
    MarginMode
)
from Shared.findError import findError
from Shared.errorSaver import errorSaver
from Shared.helpers import print_colored, convertToJsonFile
from Shared.Constant import PositionSideValues, MarketValues, MAX_PROFIT_VALUE
import time

# ****************************************************************************************************************************


_config = dotenv_values(".env")

_api_id = _config["api_id"]
_api_hash = _config["api_hash"]
_username = _config["username"]

class AbsChannel(ABC):

    _channel_id:Optional[int] = None
    # a days that we must wait for finding status of order(signal) in statistics method (such as statistic_PredictParts)
    max_day_wait:int = 15
    # a value can control unusual profit
    max_profit_percent:float = MAX_PROFIT_VALUE
    
    # determine if a message is a predict message or not
    @abstractmethod
    def isPredictMsg(self, msg:str)-> bool:
        pass
    
    # find symbol
    @abstractmethod
    async def findSymbol(self, msg:str, market:Market)-> Optional[Symbol]:
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
    
    # Check if post is a Cancel predict or not
    @abstractmethod
    async def isCancel(self, post:Post)-> bool:
        pass

    # ****************************************************************************************************************************
    # ******************************************** methods for automatic trading *************************************************
    # ****************************************************************************************************************************
   
    # find important parts of a predict message such as symbol or entry point
    @abstractmethod
    async def predictParts(self, string, post: Post)-> Optional[Predict]:
        pass 
    
    @abstractmethod
    async def extractDataFromMessage(self, msg:str):
        pass 


     
    # ****************************************************************************************************************************
    # ************************************ Test message to find details for order(signal) ****************************************
    # ****************************************************************************************************************************
    async def test(self, msg:str, showPrint:Optional[bool] = False)-> tuple[bool, str]:
        try:
            isPredict = self.isPredictMsg(msg)
            if not isPredict:
                raise Exception("Sorry, this msg is not Predict Message")

            # # ************* FIND MARKET *************
            market = await self.findMarket(msg)
            if not market:
                raise Exception("Sorry, cannot find Market")
            
            # # ************* FIND SYMBOL *************
            symbol = await self.findSymbol(msg, market)
            if not symbol:
                raise Exception("Sorry, cannot find Symbol")

            leverage = None
            if market.name != MarketValues.SPOT.value:
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
            
            is_error, is_error_message = findError(position.name if market.name != MarketValues.SPOT.value else PositionSideValues.BUY.value, profits, entries, stopLoss, leverage, self.max_profit_percent)
            if is_error:
                raise Exception(is_error_message)

            
        except Exception as e:
            if showPrint: 
                print(e)
            return False, str(e)

        if showPrint: 
            print(f'isPredict: {isPredict}\nsymbol: {symbol.name}\nmarket: {market.name}')
            if market.name != MarketValues.SPOT.value:
                print(f'position: {position.name}\nmarginMode: {marginMode.name}\nleverage: {leverage}')
            print(f'stopLoss: {stopLoss}\nentries: {entries}\nprofits: {profits}')
        

        return True, ''
    
    
    # ****************************************************************************************************************************
    # ******************************************** handle error ******************************************************************
    # ****************************************************************************************************************************

    def handleError(self, post:Post, message:str, channel_name: Optional[str] = None):
        error_post = model_to_dict(post)
        error_post['error_message'] = message
        errorSaver(data=error_post, channel_name=channel_name)

    # ****************************************************************************************************************************
    # ******************************************** statistics methods ************************************************************
    # ****************************************************************************************************************************

    # find important parts of OLD predict message such as symbol or entry point
    @abstractmethod
    async def statistic_PredictParts(self, string, post:Post):
        pass

    @abstractmethod
    async def statistic_extractDataFromMessage(self, msg:str):
        pass

   
    # main method, find statistics,  Get channel history
    async def FindStatistic(self, year:int, month:int, day:int,offset_date:Optional[int]= None)-> bool:

        if not self._channel_id:
            print('Please set _channel_id')
            return False

        client: TelegramClient = await TelegramClient(_username, _api_id, _api_hash).start()
        peer_channel =  PeerChannel(int(self._channel_id))
        telegram_channel = await client.get_entity(peer_channel)

        offset_id = 0
        limit = 100
        all_messages: list[Message] = []
        total_messages = 0
        total_count_limit = 0

        end_date = datetime(year, month, day, tzinfo=timezone.utc)

        shouldStop = False
        while not shouldStop:
            print("Current Offset ID is:", offset_id, "; Total Messages:", total_messages)
            history = await client(
            GetHistoryRequest(
                    peer=telegram_channel,
                    offset_id=offset_id,
                    # timestamp not milli timestamp
                    offset_date=offset_date,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0,
                )
            )

            if not history.messages:
                break

            messages: list[Message] = history.messages
            for message in tqdm(messages):
                message_date = message.date.replace(tzinfo=timezone.utc)
                # if start_date < message_date:
                #     continue

                if message_date < end_date:
                    shouldStop = True
                    break
                all_messages.append(message)

            offset_id = messages[len(messages) - 1].id
            total_messages = len(all_messages)
            # if total_count_limit != 0 and total_messages >= total_count_limit:
            #     break

        await client.disconnect()

        this_month = None
        for msg in reversed(all_messages):

            if not this_month:
                this_month = msg.date.month
            
            if this_month != msg.date.month:
                print_colored('waiting 5 min...', '#FFFF00')
                time.sleep(300) # 5 minutes
                this_month = msg.date.month
                

            await self.statistic_extractDataFromMessage(msg)

        return True

