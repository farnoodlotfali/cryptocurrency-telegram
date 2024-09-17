from django.db import models


class Channel(models.Model):
    channel_id = models.CharField(max_length=50)
    name = models.CharField(max_length=250)
    can_trade = models.BooleanField(default=False, editable=True, null=True)

    def __str__(self):
        return f"{self.name} {self.channel_id}"


class Symbol(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=20, editable=True)
    size = models.CharField(max_length=20, editable=True, null=True)
    fee_rate = models.CharField(max_length=20, editable=True, null=True)
    currency = models.CharField(max_length=20, editable=True, null=True)
    asset = models.CharField(max_length=20, editable=True, null=True)

    def __str__(self):
        return f"{self.name}"


class Market(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=20, editable=True)

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
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    index = models.IntegerField(editable=True, null=True)
    value = models.FloatField(default=0, editable=True, null=True)
    active = models.BooleanField(default=False, editable=True, null=True)
    period = models.CharField(max_length=60, null=True)
    date = models.DateTimeField(editable=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post.message_id} {self.value} {self.active}"


class TakeProfitTarget(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    index = models.IntegerField(editable=True, null=True)
    value = models.FloatField(default=0, editable=True, null=True)
    active = models.BooleanField(default=False, editable=True, null=True)
    period = models.CharField(max_length=60, null=True)
    date = models.DateTimeField(editable=True, null=True)
    profit = models.FloatField(default=0, editable=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.post.message_id} {self.value} {self.active}"

class SettingConfig(models.Model):
    allow_channels_set_order = models.BooleanField(default=False, editable=True, null=True)
    # how much USDT can use in open position
    max_entry_money = models.FloatField(default=5, editable=True, null=True)
    max_leverage = models.PositiveBigIntegerField(default=1, editable=True, null=True)
    leverage_effect = models.BooleanField(default=False, editable=True, null=True)
    def __str__(self):
        return f"max_entry_money: {self.max_entry_money} - allow channels set order:{self.allow_channels_set_order}"
    

    
