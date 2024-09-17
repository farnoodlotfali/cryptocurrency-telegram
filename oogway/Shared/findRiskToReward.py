
def findRiskToReward(entries, tps, stoploss):
    loss = abs(float(entries[0]) - float(stoploss))

    all_pf = 0
    for pf in tps:
        all_pf += abs(float(entries[0]) - float(pf))
    avg_RR = all_pf/len(tps)

    RR = avg_RR/loss

    # if RR < 0.2:
    #     print("error")

    return RR