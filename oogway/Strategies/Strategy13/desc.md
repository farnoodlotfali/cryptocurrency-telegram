# Strategy 13

This strategy is a real-time strategy.

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

For every prediction, we will find the status using TOHLCV data and calculate the money that the predict should give back('money_back'), and also the end time for that predict('end_date').

At first, we check all previous prediction\`s end time('end_date') according to current prediction\`s start time('start_timestamp'), if the start time is longer than the end time, we remove those predictions from the active orders list('active_orders') and the money from them is add to the current money.Then, we check the current money, if the current money is less than the positionSize, the prediction`s status is MISSED, adding to the missed orders and orders status list.


By passing the above conditions, we decrease current money by positionSize amount. we change the stoploss value according to "max_percent_stoploss" and first entry and predict position(LONG, SHORT) and also we change take-profit according to "max_percent_tp" and first entry and predict position(LONG, SHORT)value.The prediction is added to the active orders and pending orders.

<mark>Then we reverse the predict. it means that we change the LONG to SHORT(SHORT to LONG), take-profit is updated to stoploss value and stoploss value is updated to take-profit value</mark>


Now it's time to evaluate the status. Wait until the start time('start_timestamp') reaches. Wait until the entry point is reached, if reached, it is removed from the pending list. Wait until the take-profit point or stoploss point hits.

If stoploss hits, we calculate the loss amount, then find the prediction from active orders list and update its ('money_back') and ('end_date'). The prediction\`s status is LOSS , adding to the orders status list and the evaluation breaks.

If take-profit hits, we calculate the profit amount, then find the prediction from active orders list and update its ('money_back'). The prediction\`s status is PROFIT , adding to the orders status list. Then we  break the evaluation. Then find the prediction from the active orders list and update its ('money_back') and ('end_date').




   