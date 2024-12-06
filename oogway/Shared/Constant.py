from enum import Enum

class PostStatusValues(Enum):
    FAILED_WITH_PROFIT = 'FAILED WITH PROFIT'
    SUCCESS = 'SUCCESS'
    FULLTARGET = 'FULLTARGET'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'
    PENDING = 'PENDING'
    ERROR = 'ERROR'
    TREND_ERROR = 'TREND_ERROR'
    WAIT_MANY_DAYS = 'WAIT MANY DAYS'
    MISSED = 'MISSED'

class PostStatusTypeValues(Enum):
    FAILED_WITH_PROFIT = [PostStatusValues.FAILED_WITH_PROFIT.value,1,2,3,4,5,6,7,8]
    SUCCESS = [PostStatusValues.SUCCESS.value,1,2,3,4,5,6,7,8]
    FULLTARGET = [PostStatusValues.FULLTARGET.value,1000]
    FAILED = [PostStatusValues.FAILED.value,-1]
    CANCELED = [PostStatusValues.CANCELED.value,0]
    PENDING = [PostStatusValues.PENDING.value,0]
    ERROR = [PostStatusValues.ERROR.value,0]
    TREND_ERROR = [PostStatusValues.TREND_ERROR.value,0]
    MISSED = [PostStatusValues.MISSED.value,0]
    WAIT_MANY_DAYS = [PostStatusValues.WAIT_MANY_DAYS.value,0]


class MarketValues(Enum):
    SPOT = 'SPOT'
    FUTURES = 'FUTURES'


class PositionSideValues(Enum):
    LONG = 'LONG'
    SHORT = 'SHORT'
    BUY = 'BUY'


class MarginModeValues(Enum):
    ISOLATED = 'ISOLATED'
    CROSS = 'CROSS'

class TrendValues(Enum):
    UPTREND = 'UPTREND'
    DOWNTREND = 'DOWNTREND'
    SIDEWAYS = 'SIDEWAYS'


class OrderSide(Enum):
    BUY = 'buy'
    SELL = 'sell'

class OrderType(Enum):
    LIMIT = 'limit'
    MARKET = 'market'

# 60 percent
MAX_PROFIT_VALUE = 60


# # for webPanel you can check SettingConfig model in PostAnalyzer\models.py
SETTING_CONFIGS_VARIABLES = {
    # Allow channels set order 
    'allow_channels_set_order': True,
    # A number that show how much USDT can use in open a position
    'max_entry_money': 20,
    # A number that times Profit or Loss <u>(Leverage Effect must be ON)
    'max_leverage': 20,
    # If True, leverage has Effect to a order. else Max leverage will be 1
    'leverage_effect': True
}