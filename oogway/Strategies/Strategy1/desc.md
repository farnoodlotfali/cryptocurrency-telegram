# Strategy 1

This strategy is a real-time strategy.
This strategy actually does the same strategy as the channel itself.
### Initial Strategy
---
money = is a mount of money that we want to use it in this strategy. Required

timeZone =  is a time zone. default = UTC

### Running Parameters
---

predicts = a list of predict. Required

close_tp =  is a take-profit index that the order must be close. default = 1

showPrint = is a flag that allow to print a details. default = False

positionSize = is a mount of money for opening a order. default = 100

## How it works
This strategy just act like channels strategy. So we Evaluate channels strategy.

For every prediction, we will find the status using TOHLCV data and calculate the money that the predict should give back('money_back'), and also the end time for that predict('end_date').

At first, we check all previous prediction\`s end time('end_date') according to current prediction\`s start time('start_timestamp'), if the start time is longer than the end time, we remove those predictions from the active orders list('active_orders') and the money from them is add to the current money.Then, we check the current money, if the current money is less than the positionSize, the prediction`s status is MISSED, adding to the missed orders and orders status list.

By passing the above conditions, we decrease current money by positionSize amount.