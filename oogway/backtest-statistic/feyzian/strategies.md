# Strategy 1
This strategy actually does the same strategy as the channel itself.\
the "tp_status_array" is a success array that can be includes ["SUCCESS", "FULLTARGET"].\
"failed_status_array" is a success array that can be includes ["FAILED", "FAILED WITH PROFIT"].

the "my_money" is a initial money.\
the "close_tp" is a take-profit index that the order must be close. default = 0\
the "showPrint" is a flag that allow to print a details. default = False\
the "positionSize" is a mount of money for opening a order. default = 100

### How It Works
if status of predict is in the "failed_status_array":\
at first we get "TakeProfitTarget" to handle predicts with status of "FAILED WITH PROFIT" according to "close_tp". if close_tp is smaller than tp_queryset, it is a success and "is_tp" flag will be TRUE\
else it will decrease "my_money".\
($my\_money - positionSize - loss$) 

if status of predict is in the "tp_status_array" or "is_tp":\
at first we get all "TakeProfitTarget" and find tp length and active_count. then we check if the predict is fulltarget.\
if "is_full" and "close_tp" is bigger than "tp_queryset", we will get the last TP.\
elseif "active_count" is smaller than "close_tp", we will get TP that is tp_queryset[\"close_tp"].\
else the predict is a "PENDING" status.\

the "my_money" will be increase.\
($my\_money + positionSize + profit$) 

if the predict`s status is "PENDING":\
just decrease the "my_mony".\
($my\_money - positionSize$) 

<br/>

---

# Strategy 2
the "my_money" is a initial money.\
the "close_tp" is a take-profit index that the order must be close. default = 0\
the "showPrint" is a flag that allow to print a details. default = False\
the "positionSize" is a mount of money for opening a order. default = 100\
the "max_percent_stoploss" is a percent that changes the stoploss value according to first entry. default = 5 (%)\

### How It Works

This strategy changes the stoploss value according to "max_percent_stoploss" and first entry and predict position(LONG, SHORT). 

$$
\text{stop\_loss} = \text{first\_entry} \times \left( 1 + \left( \frac{\text{max\_percent\_stoploss}}{100 \times \text{leverage} \times (1 \text{ if isSHORT else } -1)} \right) \right)
$$\


it loads OHLC data from a json file.
it wait until "start_timestamp" reaches.
due to change stoploss, we must check take-profits and entries from scratch. In addition, we take out the profit when it hits each take-profit. then we update the entry. so entry will change to the previous take-profit value. and stoploss value will change to entry value in the first time; in other times, it will change to two previous take-profit values.\
this strategy will continue until hits all take-profits or the stop loss, or take-profits length is equal to "close_tp".

TODO
- [] implement "my_mony" calculation
<br/>

---

# Strategy 3

the "my_money" is a initial money.\
the "close_tp" is a take-profit index that the order must be close. default = 0\
the "showPrint" is a flag that allow to print a details. default = False\
the "positionSize" is a mount of money for opening a order. default = 100\
the "max_percent_stoploss" is a percent that changes the stoploss value according to first entry. default = 5 (%)\
the "effect_stoploss" is a flag for "max_percent_stoploss", that if it is TRUE, the stoploss will be change according to "max_percent_stoploss". on the other hand the stoploss is not changed. default = True\

### How It Works

**This strategy acts like strategy 2 with small differences**.\
This strategy changes the stoploss value according to "max_percent_stoploss" and first entry and predict position(LONG, SHORT). 

`if "effect_stoploss" true:`
$$
\text{stop\_loss} = \text{first\_entry} \times \left( 1 + \left( \frac{\text{max\_percent\_stoploss}}{100 \times \text{leverage} \times (1 \text{ if isSHORT else } -1)} \right) \right)
$$\

**this strategy just updates the entry, and stoploss never changes.(stoploss is constant)**

it loads OHLC data from a json file.
it wait until "start_timestamp" reaches.
due to change stoploss, we must check take-profits and entries from scratch. In addition, we take out the profit when it hits each take-profit. then we update the entry. so entry will change to the previous take-profit value.\
this strategy will continue until hits all take-profits or the stop loss, or take-profits length is equal to "close_tp".

TODO
- [] implement "my_mony" calculation
<br/>

---

# Strategy 4

the "my_money" is a initial money.\
the "close_tp" is a take-profit index that the order must be close. default = 0\
the "showPrint" is a flag that allow to print a details. default = False\
the "positionSize" is a mount of money for opening a order. default = 100\
the "max_percent_stoploss" is a percent that changes the stoploss value according to first entry. default = 5 (%)\

### How It Works

This strategy changes the stoploss value according to "max_percent_stoploss" and first entry and predict position(LONG, SHORT) **just for the first time**

$$
\text{stop\_loss} = \text{first\_entry} \times \left( 1 + \left( \frac{\text{max\_percent\_stoploss}}{100 \times \text{leverage} \times (1 \text{ if isSHORT else } -1)} \right) \right)
$$\

this strategy never changes the entry and stoploss. due to change stoploss, we must check take-profits and entries from scratch.\
this strategy will continue until hits all take-profits or the stop loss, or take-profits length is equal to "close_tp".

TODO
- [] implement "my_mony" calculation