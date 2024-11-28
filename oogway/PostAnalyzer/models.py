from django.db import models


class Channel(models.Model):
    channel_id = models.CharField(max_length=50)
    name = models.CharField(max_length=250)
    can_trade = models.BooleanField(default=False, editable=True, null=True)

    def __str__(self):
        return f"{self.name} {self.channel_id}"

class Market(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=20, editable=True)

    def __str__(self):
        return f"{self.name}"
    

class Symbol(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=40, editable=True)
    min_trade_amount = models.CharField(max_length=20, editable=True, null=True)
    quote = models.CharField(max_length=20, editable=True, null=True)
    base = models.CharField(max_length=20, editable=True, null=True)
    # exchange = models.CharField(max_length=20, editable=True, null=True)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, null=True)
    
    def __str__(self):
        return f"{self.name}"


class PostStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=35, editable=True)
    type = models.IntegerField(default=0, editable=True, null=True)

    def __str__(self):
        return f"{self.name} {self.type} "

class PositionSide(models.Model):
    name = models.CharField(max_length=50, editable=True) 

    def __str__(self):
        return f"{self.name}"
    
class MarginMode(models.Model):
    name = models.CharField(max_length=50, editable=True) 

    def __str__(self):
        return f"{self.name}"
    
class Post(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateTimeField(editable=True)
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, editable=True, null=True
    )
    message_id = models.CharField(max_length=50)
    message = models.CharField(max_length=6000, editable=True)
    reply_to_msg_id = models.CharField(max_length=15, null=True)
    edit_date = models.CharField(max_length=100, editable=True, null=True)
    is_predict_msg = models.BooleanField(default=False, editable=True, null=True)

    def __str__(self):
        return f"{self.message_id} {self.channel.channel_id}"


class Predict(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    status = models.ForeignKey(PostStatus, on_delete=models.CASCADE)
    position = models.ForeignKey(PositionSide, on_delete=models.CASCADE,editable=True)
    margin_mode = models.ForeignKey(MarginMode, on_delete=models.CASCADE, editable=True, null=True,default=None)
    leverage = models.IntegerField(default=1, editable=True, null=True)
    stopLoss = models.FloatField(editable=True, null=True)
    profit = models.FloatField(default=0, editable=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=50, editable=True, null=True, default=None, blank=True)
    date = models.DateTimeField(editable=True, null=True)

    def __str__(self):
        return f"{self.symbol.name} {self.market.name} {self.position.name} {self.status.name} {self.leverage}"


class EntryTarget(models.Model):
    predict = models.ForeignKey(Predict, on_delete=models.CASCADE)
    index = models.IntegerField(editable=True, null=True)
    value = models.FloatField(default=0, editable=True, null=True)
    active = models.BooleanField(default=False, editable=True, null=True)
    period = models.CharField(max_length=60, null=True)
    date = models.DateTimeField(editable=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.predict.id} {self.value} {self.active}"


class TakeProfitTarget(models.Model):
    predict = models.ForeignKey(Predict, on_delete=models.CASCADE)
    index = models.IntegerField(editable=True, null=True)
    value = models.FloatField(default=0, editable=True, null=True)
    active = models.BooleanField(default=False, editable=True, null=True)
    period = models.CharField(max_length=60, null=True)
    date = models.DateTimeField(editable=True, null=True)
    profit = models.FloatField(default=0, editable=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.predict.id} {self.value} {self.active}"
    
class StopLoss(models.Model):
    predict = models.ForeignKey(Predict, on_delete=models.CASCADE)
    value = models.FloatField(default=0, editable=True, null=True)
    period = models.CharField(max_length=60, null=True)
    date = models.DateTimeField(editable=True, null=True)
    profit = models.FloatField(default=0, editable=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.predict.id} {self.value}"

class SettingConfig(models.Model):
    # Allow channels set order 
    allow_channels_set_order = models.BooleanField(default=False, editable=True, null=True)
    # A number that show how much USDT can use in open a position
    # how much USDT can use in open position
    max_entry_money = models.FloatField(default=5, editable=True, null=True)
    # A number that times Profit or Loss <u>(Leverage Effect must be ON)
    max_leverage = models.PositiveBigIntegerField(default=1, editable=True, null=True)
    # If True, leverage has Effect to a order. else Max leverage will be 1
    leverage_effect = models.BooleanField(default=False, editable=True, null=True)
    def __str__(self):
        return f"max_entry_money: {self.max_entry_money} - allow channels set order:{self.allow_channels_set_order}"
    

    
