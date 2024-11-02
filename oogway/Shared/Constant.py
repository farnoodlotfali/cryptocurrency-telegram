from enum import Enum

class PostStatusValues(Enum):
    FAILED_WITH_PROFIT = 'FAILED WITH PROFIT'
    SUCCESS = 'SUCCESS'
    FULLTARGET = 'FULLTARGET'
    FAILED = 'FAILED'
    CANCELED = 'CANCELED'
    PENDING = 'PENDING'
    ERROR = 'ERROR'
    WAIT_MANY_DAYS = 'WAIT MANY DAYS'

class PostStatusTypeValues(Enum):
    FAILED_WITH_PROFIT = [PostStatusValues.FAILED_WITH_PROFIT.value,1,2,3,4,5,6,7,8]
    SUCCESS = [PostStatusValues.SUCCESS.value,1,2,3,4,5,6,7,8]
    FULLTARGET = [PostStatusValues.FULLTARGET.value,1000]
    FAILED = [PostStatusValues.FAILED.value,-1]
    CANCELED = [PostStatusValues.CANCELED.value,0]
    PENDING = [PostStatusValues.PENDING.value,0]
    ERROR = [PostStatusValues.ERROR.value,0]
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


# # for webPanel you can check SettingConfig model in PostAnalyzer\models.py
# SettingConfigsVariables = {
#     # a days that we must wait for finding status of order(signal) in statistics method (such as statistic_PredictParts )
#     'max_day_wait': 10,
# }