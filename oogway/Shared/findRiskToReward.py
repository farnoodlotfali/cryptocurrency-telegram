
def findRiskToReward(entries, tps, stoploss):
    loss = abs(float(entries[0]) - float(stoploss))

    all_pf = 0
    for tp in tps:
        all_pf += abs(float(entries[0]) - float(tp))
    avg_profit = all_pf/len(tps)

    RR = avg_profit/loss

    # if RR < 0.2:
    #     print("error")

    return RR