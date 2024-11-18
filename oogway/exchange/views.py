
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from Shared.Exchange import exchange
from PostAnalyzer.models import (
    Market,
    Symbol,
    Predict,
    PostStatus
)
from Shared.Constant import MarketValues
from django.shortcuts import redirect


LOGIN_PAGE_URL = "/panel/login"


# save symbols
@login_required(login_url=LOGIN_PAGE_URL)
def save_symbols(request):
    order_data = exchange.fetch_markets()

    spot_market = Market.objects.get(name=MarketValues.SPOT.value)
    future_market = Market.objects.get(name=MarketValues.FUTURES.value)

    for symbol in order_data:
        if symbol["quote"] == "USDT":
            newSymbol = {
                "name": symbol["symbol"],
                "min_trade_amount": symbol["limits"]["amount"]["min"],
                "quote": symbol["quote"],
                "base": symbol["base"],
                "market": spot_market if symbol["spot"] else future_market,
            }
           
            if not Symbol.objects.filter(
                name=newSymbol["name"],
                market=newSymbol["market"]
            ).exists():
                    newSymbol = Symbol(**newSymbol)
                    newSymbol.save()

    return JsonResponse(order_data, safe=False)


# cancel order
@login_required(login_url=LOGIN_PAGE_URL)
def cancel_order(request, symbol, order_id=None, market=None):
    print(symbol, order_id, market)
    try:
        res = exchange.cancel_order(id=order_id,symbol=symbol)
        print(res)
        predict = Predict.objects.filter(order_id=order_id).first()
        if predict:
            cancelStatus = PostStatus.objects.get(name="CANCELED")
            predict.status = cancelStatus
            predict.save()
    except:
        print("error")

    return redirect("Panel:predict")
