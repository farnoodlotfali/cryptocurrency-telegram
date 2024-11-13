from abc import ABC
from django.forms.models import model_to_dict
from PostAnalyzer.models import (
    Predict,
)
from typing import Optional
import pytz
from Shared.helpers import print_colored
from datetime import datetime
import pandas as pd
import os
# ***************************************************************************************************************************************************

class AbsStrategy(ABC):
    strategy_name = 'strategy_name'

    time_zone = 'UTC'
    # time_zone = 'Asia/Tehran'
    time_zone_pytz = pytz.timezone(time_zone)


    # loss
    total_loss:float = 0
    loss_count:int = 0

    # profit
    total_profit = 0
    profit_count:int  = 0

    # pending
    total_pending_money:float  = 0
    pending_count:int  = 0

    # 
    initial_money:float  = 0
    current_money:float  = 0
    total_opening_orders:int = 0

    # 
    history = []

    # missing 
    missed_orders = [
        # model_to_dict(Predict)
    ]    
    
    # missing 
    pending_orders = [
        # model_to_dict(Predict)
    ]

    # stack active order
    active_orders = [
        # {     
        #     'id': 1,
        #     'symbol': "",
        #     'start_date': "",
        #     'end_date': "",
        #     'money_used': "",
        #     'money_back': "",
        # }
    ]

    # orders history
    orders_status = [
        # {
        #     'date': 12345,
        #     'active_date': 12345,
        #     'symbol': "",
        #     'profit': 0,
        #     'status': "",
        #     'status_date': 12345,
        #     'status_type': 0,
        #     'market': "",
        #     'position': "",
        #     'leverage': 1,
        #     'id': 1,
        # }
    ]


    def __init__(self, money: float, timeZone:str='UTC'):
        self.time_zone = timeZone
        self.time_zone_pytz = pytz.timezone(timeZone)
        self.initial_money = money
        self.current_money = money
        self.total_loss = 0
        self.loss_count = 0
        self.total_profit = 0
        self.profit_count = 0
        self.total_pending_money = 0
        self.pending_count = 0
        self.total_opening_orders = 0
        self.history = []
        self.missed_orders = []
        self.pending_orders = []
        self.active_orders = []
        self.orders_status = []


    # this method should update active_orders
    def updateMoneyManagement(self, id:int, end_date:Optional[int]=None, money_back: Optional[float]=None, start_date:Optional[int]=None):
        
        for item in self.active_orders:
            if item['id'] == id:
                if end_date:
                    item['end_date'] = end_date 
                if start_date:
                    item['start_date'] = start_date 
                if money_back:
                    item['money_back'] = money_back
        
                break

    # this method should add order to pending_orders and orders_status for PENDING order
    def addPendingOrder(self, order:Predict):
        self.pending_orders.append(model_to_dict(order))
        self.orders_status.append({
            'date': order.date.astimezone(self.time_zone_pytz),
            'active_date': None,
            'symbol': order.symbol.name,
            'profit': 0,
            'status': "PENDING",
            'status_date': None,
            'status_type': 0,
            'market': order.market.name,
            'position': order.position.name,
            'leverage': order.leverage,
            'id': order.id,
        })

    # this method should remove order to pending_orders and orders_status for PENDING order
    def removeFromPending(self, order:Predict):
        for item in self.pending_orders:
            if order.id == item['id']:
                self.pending_orders.remove(item)

        for item in self.orders_status:
            if order.id == item['id']:
                self.orders_status.remove(item)

    # this method should add order to missed_orders and orders_status for MISSED order
    def addMissOrder(self, order:Predict):
        self.missed_orders.append(model_to_dict(order))
        self.orders_status.append({
            'date': order.date.astimezone(self.time_zone_pytz),
            'active_date': None,
            'symbol': order.symbol.name,
            'profit': 0,
            'status': "MISSED",
            'status_date': None,
            'status_type': 0,
            'market': order.market.name,
            'position': order.position.name,
            'leverage': order.leverage,
            'id': order.id,
        })

    # this method should add order and update orders_status for orders that them entry point is touched
    def addEntryOrder(self, order:Predict, active_date:int):
        """
            status_date is timestamp
        """
        # will handle milli second timestamp
        if len(str(active_date)) == 13:
            active_date = active_date/1000

        self.orders_status.append({
            'date': order.date.astimezone(self.time_zone_pytz),
            'active_date': datetime.fromtimestamp(active_date).astimezone(self.time_zone_pytz),
            'symbol': order.symbol.name,
            'profit': 0,
            'status': "ENTRY",
            'status_date': None,
            'status_type': 0,
            'market': order.market.name,
            'position': order.position.name,
            'leverage': order.leverage,
            'id': order.id,
        })

    # this method should update orders_status list for LOSS status
    def addLossOrder(self, order:Predict, status_date:int, profit:float):
        """
            status_date is timestamp
        """
        # will handle milli second timestamp
        if len(str(status_date)) == 13:
            status_date = status_date/1000

        for item in self.orders_status:
            if item['id'] == order.id:
                item['profit'] = profit
                item['status_date'] = datetime.fromtimestamp(status_date).astimezone(self.time_zone_pytz)
                item['status'] = "LOSS"
                item['status_type'] = -1
                break
        
    # this method should update orders_status list for PROFIT status
    def addProfitOrder(self, order:Predict, status_date:int , profit:float, type:int):
        """
            status_date is timestamp
        """
        # will handle milli second timestamp
        if len(str(status_date)) == 13:
            status_date = status_date/1000

        for item in self.orders_status:
            if item['id'] == order.id:
                item['profit'] = profit
                item['status_date'] = datetime.fromtimestamp(status_date).astimezone(self.time_zone_pytz)
                item['status'] = "PROFIT"
                item['status_type'] = type
                break

    # this method should calculate value of profit according to positionSize
    def calProfit(self, positionSize: float, profit: float)-> float:
        return positionSize*(profit/100)
    
    # this method should control detail of order to history 
    def orderDetailController(self, predict: Predict, stopLoss:float, take_profit_targets: list, entry_targets: list, stopLoss_time:list):
        # model = model_to_dict(predict)
        model = {}
        model['symbol'] = predict.symbol.name
        model['market'] = predict.market.name
        model['position'] = predict.position.name

        model['stopLoss'] = stopLoss
        model['stopLoss_time'] = stopLoss_time

        model['tps'] = take_profit_targets

        model['ens'] = entry_targets


        self.history.append(model)

    # this method should create and add order to active_orders
    def addActiveOrder(self, order:Predict, positionSize:float):
        self.active_orders.append({
            'id': order.id,
            'symbol': order.symbol.name,
            'start_date': float('inf'),
            'end_date': float('inf'),
            'money_used': positionSize,
            'money_back': positionSize,
        })

    # this method should return all blocked money(the money currently are not available) from active_orders
    def giveBackAllActiveMoney(self):
        for item in self.active_orders:
            self.current_money += item['money_back']


    # this method should find and return all free money according to start_date. it should compare the start_time and end_date of all previous order. from active_orders
    def checkFreeMoneyManagement(self, start_date:int):
        free_money = 0
        for item in self.active_orders:
            if start_date > item['end_date']:
                free_money += item['money_back']
                self.active_orders.remove(item)

        return free_money
    
    # this method should find blocked money(the money currently are not available) from active_orders
    def checkFBlockedMoneyManagement(self):
        blocked_money = 0
        for item in self.active_orders:
            if item['end_date'] == float('inf'):
                blocked_money += item['money_back']

        return blocked_money

    # generate a report
    def report(self):
        print_colored(f"initial money: {self.initial_money}", "gold")
        print_colored(f"total_opening_orders: {self.total_opening_orders}", "#1da44f")
        print_colored(f"total_loss: {self.total_loss}", "pink")
        print_colored(f"total_profit: {self.total_profit}", "green")
        print_colored(f"gross: {self.total_profit+self.total_loss}", "deeppink")
        print_colored(f"total_pending: {self.total_pending_money}", "grey")
        print_colored(f"my free money: {self.current_money-self.total_pending_money}", "orange")
        print_colored(f"my total money: {self.current_money}", "#d16984")
        print_colored(f"profit_count: {self.profit_count}, loss_count: {self.loss_count}, pending_count: {self.pending_count}, missed_count: {len(self.missed_orders)}", "#a1309d")

        date = datetime.today().date()
        hour = datetime.today().hour
        minute = datetime.today().minute
        second = datetime.today().second

        path_folder = os.path.join(os.path.dirname(__file__), "../strategy-reports")
        os.makedirs(path_folder, exist_ok=True)
        df = pd.DataFrame(self.orders_status)
        df.to_csv(f'{path_folder}/report-{date}-{hour}-{minute}-{second}-{self.strategy_name}.csv', index=False)

        # df = pd.DataFrame(self.history)
        # df.to_csv(f'{path_folder}/report-{name}-history-{self.strategy_name}.csv', index=False)
        
                
    






