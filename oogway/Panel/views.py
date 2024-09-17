from bingx.api import BingxAPI
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core import serializers
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from dotenv import dotenv_values
from PostAnalyzer.models import (
    Channel,
    EntryTarget,
    Market,
    Post,
    PostStatus,
    Predict,
    Symbol,
    TakeProfitTarget,
    SettingConfig,
    PositionSide
)
from telethon.sync import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import asyncio
from django.db.models import Count,Q,Sum, F
import datetime
from django.forms.models import model_to_dict
from django import template
from Shared.Exchange import exchange
from Shared.SymbolConverter import SymbolConverter

config = dotenv_values(".env")
API_KEY = config["API_KEY"]
SECRET_KEY = config["SECRET_KEY"]
bingx = BingxAPI(API_KEY, SECRET_KEY, timestamp="local")

def get_posts_api(request):
    posts = Post.objects.all()  # Fetch all posts from the database
    data = serializers.serialize("json", posts)

    return JsonResponse(data, safe=False)


def get_symbols_api(request):
    symbols = Symbol.objects.all()  # Fetch all symbols from the database
    data = serializers.serialize("json", symbols)
    # print(symbols)
    return JsonResponse(data, safe=False)


@login_required(login_url="login")
def home(request):
    channels = Channel.objects.all()
    predicts = Predict.objects.all()
    
    return render(request, "Home/home.html", {"channels": channels,"predicts": predicts})

def advance_test(request):
    return render(request, "advanced.html")

def widgets_test(request):
    return render(request, "widgets.html")

def charts_test(request):
    return render(request, "chartjs.html")

def validation_test(request):
    return render(request, "validation.html")


class CustomLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user
        if user.is_superuser:
            return "/panel"


# symbols
@login_required(login_url="login")
def get_symbols(request):
    symbols = Symbol.objects.all()
    return render(request, "Symbol/index.html", {"symbols": symbols})


# markets
@login_required(login_url="login")
def get_markets(request):
    markets = Market.objects.all()
    return render(request, "Market/index.html", {"markets": markets})


# predicts
@login_required(login_url="login")
def get_predicts(request):
    predicts = Predict.objects.all()
    symbol_param = request.GET.get("symbol")
    channel_param = request.GET.get("channel")
    
    if symbol_param:
        predicts = predicts.filter(symbol__name=symbol_param)
    if channel_param:
        predicts = predicts.filter(post__channel__channel_id=channel_param)
    
    symbols = Symbol.objects.all()
    channels = Channel.objects.all()
    # result = Predict.objects.filter(
    #     Q(status__name='FAILED') 
    #     # Q(status__name='SUCCESS') | Q(status__name='FAILED WITH PROFIT')
    # )

    # # print(result)
    # total_profit = 0
    # for x in result:
    #     total_profit +=x.profit
    # print(total_profit)
    # max_date = datetime.date(2024, 6, 24)
    # min_date = datetime.date(2024, 6, 12)

    # results = Predict.objects.filter(
    #     date__lte=max_date,
    #     date__gte=min_date,
    #     position__name="SHORT"
    # ).values('status__name').annotate(
    # total_profit=Sum(F('profit')),
    # count_profit=Count('profit'),
    
    # )
    # print(results)
    
    return render(
        request,
        "Predict/index.html",
        {"predicts": predicts, "symbols": symbols, "symbol_param": symbol_param, "channels": channels, "channel_param": channel_param,},
    )


# channels
@login_required(login_url="login")
def channel_list(request):
    channels = Channel.objects.all()
    return render(request, "Channel/channelList.html", {"channels": channels})


# channels
@login_required(login_url="login")
def change_channel_trade(request, channel_id):
    channel = Channel.objects.get(channel_id=channel_id)
    channel.can_trade = not channel.can_trade
    channel.save()
    return redirect("Panel:channel_list")


# channel detail
@login_required(login_url="login")
def channel_detail(request, channel_id):
    channel = get_object_or_404(Channel, channel_id=channel_id)
    return render(request, "Channel/channelDetail.html", {"channel": channel})


# posts list
@login_required(login_url="login")
def post_list(request):
    posts = Post.objects.all().order_by("-id")
    return render(request, "Post/postList.html", {"posts": posts})


# post detail
@login_required(login_url="login")
def post_detail(request, post_id):
    post = Post.objects.get(pk=post_id)

    related_posts = Post.objects.filter(reply_to_msg_id=post.message_id)

    predict = None
    entries = None
    take_profits = None
    if post.is_predict_msg:
        predict = Predict.objects.get(post=post)
        entries = EntryTarget.objects.filter(post=post)
        take_profits = TakeProfitTarget.objects.filter(post=post)

    return render(
        request,
        "Post/postDetail.html",
        {
            "post": post,
            "related_posts": related_posts,
            "predict": predict,
            "entries": entries,
            "take_profits": take_profits,
        },
    )


# post detail
@login_required(login_url="login")
def save_coins_from_api(request):
    order_data = bingx.get_all_contracts()

    for symbol in order_data:
        if symbol["currency"] == "USDT":
        # print(symbol["currency"])
            newSymbol = {
                "name": symbol["symbol"],
                "size": symbol["size"],
                "fee_rate": symbol["feeRate"],
                "currency": symbol["currency"],
                "asset": symbol["asset"],
            }
            newSymbol = Symbol(**newSymbol)

            newSymbol.save()

    # data = serializers.serialize("json", order_data)

    # return JsonResponse(data, safe=False)


# cancel order
@login_required(login_url="login")
def cancel_order(request, symbol, order_id=None, market=None):
    # try:
    #     res = bingx.cancel_order(symbol,order_id, order_id)
    #     # res = bingx.cancel_all_orders_of_symbol(symbol)
    #     predict = Predict.objects.get(order_id=order_id)
    #     cancelStatus = PostStatus.objects.get(name="CANCELED")
    #     predict.status = cancelStatus
    #     print(111)
    #     print(res)
    #     predict.save()
    # except:
    #     print("error")

    try:
        exchange.cancel_order(id=order_id,symbol=SymbolConverter(symbol, market))
        predict = Predict.objects.get(order_id=order_id)
        cancelStatus = PostStatus.objects.get(name="CANCELED")
        predict.status = cancelStatus
        predict.save()
    except:
        print("error")
    # data = serializers.serialize("json", order_data)

    return redirect("Panel:predict")

# change predict status
@login_required(login_url="login")
def change_predict_status(request, predict_id, status):
    try:
        predict = Predict.objects.get(pk=predict_id)
        newStatus = PostStatus.objects.get(name=status)
        predict.status = newStatus
        predict.save()
    except:
        print("error")

    return redirect("Panel:predict")

def tp_index_stat(request):
    position_param = request.GET.get("position")
    dateTo_param = request.GET.get("dateTo")
    dateFrom_param = request.GET.get("dateFrom")
    channel_param = request.GET.get("channel")
    symbol_param = request.GET.get("symbol")
    # print(channel_param)

    query_filters = {}
    if channel_param:
        query_filters['post__channel__channel_id'] = channel_param 
    if position_param:
        query_filters['position__name'] = position_param
    if dateTo_param:
        query_filters['date__lte'] = dateTo_param
    if dateFrom_param:
        query_filters['date__gte'] = dateFrom_param
    if symbol_param:
        query_filters['symbol__name'] = symbol_param
     # *****************************************
    tp_indexes = Predict.objects.filter(Q(status__name="FAILED WITH PROFIT") | Q(status__name="FULLTARGET")| Q(status__name="SUCCESS"),**query_filters)

    tp_indexes_stat = {
        "FWP_is_success":{
            "tp1":0,
            "tp2":0,
            "tp3":0,
            "tpBIG":0,
            "full":0,
        },
        "FWP_is_failed":{
            "tp1":0,
            "tp2":0,
            "tp3":0,
            "tpBIG":0,
            "full":0,
        },
        "profits":{
            "tp1": {"profit":0,"count":0},
            "tp2":{"profit":0,"count":0},
            "tp3":{"profit":0,"count":0},
            "tpBIG":{"profit":0,"count":0},
            "full":{"profit":0,"count":0},
        },
        
    }   
  
    for pr in tp_indexes:
        tp = TakeProfitTarget.objects.filter(post=pr.post, active=True).order_by('-index').first()
        index = int(tp.index)+1
        # print(pr.symbol.name,index)
        if index == 1:
            if pr.status.name != "FAILED WITH PROFIT":
                tp_indexes_stat["FWP_is_failed"]["tp1"] +=1

            tp_indexes_stat["FWP_is_success"]["tp1"] +=1
            tp_indexes_stat["profits"]["tp1"]['profit'] += float(tp.profit)
            tp_indexes_stat["profits"]["tp1"]['count'] += 1
        elif index == 2:
            if pr.status.name != "FAILED WITH PROFIT":
                tp_indexes_stat["FWP_is_failed"]["tp2"] +=1

            tp_indexes_stat["FWP_is_success"]["tp2"] +=1
            tp_indexes_stat["profits"]["tp2"]['profit'] += float(tp.profit)
            tp_indexes_stat["profits"]["tp2"]['count'] += 1

        elif index == 3:
            if pr.status.name != "FAILED WITH PROFIT":
                tp_indexes_stat["FWP_is_failed"]["tp3"] +=1

            tp_indexes_stat["FWP_is_success"]["tp3"] +=1
            tp_indexes_stat["profits"]["tp3"]['profit'] += float(tp.profit)
            tp_indexes_stat["profits"]["tp3"]['count'] += 1

        elif index > 3:
            if pr.status.name == "FULLTARGET":
                tp_indexes_stat["FWP_is_failed"]["full"] +=1
                tp_indexes_stat["FWP_is_success"]["full"] +=1
                tp_indexes_stat["profits"]["full"]['profit'] += float(tp.profit)
                tp_indexes_stat["profits"]["full"]['count'] += 1

            else:
                if pr.status.name != "FAILED WITH PROFIT":
                    tp_indexes_stat["FWP_is_failed"]["tpBIG"] +=1

                tp_indexes_stat["FWP_is_success"]["tpBIG"] +=1
                tp_indexes_stat["profits"]["tpBIG"]['profit'] += float(tp.profit)
                tp_indexes_stat["profits"]["tpBIG"]['count'] += 1
            
   
    return tp_indexes_stat

# charts
def predict_status_chart(request):
    statuses = PostStatus.objects.all()

    status_dict = dict()

    for status in statuses:
        status_dict[status.name] = 0

    grouped_predictions = (Predict.objects.values('status__name').annotate(prediction_count=Count('id')))

    for group in grouped_predictions:
        status_dict[group['status__name']] = group["prediction_count"]


    predictsGroup = {
        "labels": list(status_dict.keys()),
        "data": list(status_dict.values()),
    }

    return JsonResponse(predictsGroup)

def channel_predict_status_chart(request):
    statuses = PostStatus.objects.all()

    channel_counts = Channel.objects.values('name').annotate(
        **{status.name: Count('post__predict__status', filter=Q(post__predict__status__name=status.name)) for status in statuses}
    )

    # print(channel_counts)

    channel_status_count_dict = {}

    for channel in channel_counts:
        channel_name = channel['name']
        channel_status_count_dict[channel_name] = {
           status.name: channel[status.name] for status in statuses
        }

    # print(list(channel_status_count_dict.keys()))
    # print(list(channel_status_count_dict.values()))

    
    return JsonResponse({
        "labels": list(channel_status_count_dict.keys()),
        "data": list(channel_status_count_dict.values()),
    })

def criteria_chart_for_channel(request):
    position_param = request.GET.get("position")
    dateTo_param = request.GET.get("dateTo")
    dateFrom_param = request.GET.get("dateFrom")
    channel_param = request.GET.get("channel")
    symbol_param = request.GET.get("symbol")
    
    # print(channel_param)

    query_filters = {}
    if channel_param:
        query_filters['post__channel__channel_id'] = channel_param 
    if position_param:
        query_filters['position__name'] = position_param
    if dateTo_param:
        query_filters['date__lte'] = dateTo_param
    if dateFrom_param:
        query_filters['date__gte'] = dateFrom_param
    if symbol_param:
        query_filters['symbol__name'] = symbol_param
    results = Predict.objects.filter(
      **query_filters
    ).values('status__name').annotate(
        total_profit=Sum(F('profit')),
        count=Count('profit'),
    )

    predict_justSuc = Predict.objects.filter(status__name="FAILED WITH PROFIT",**query_filters)
    t = 0
    for predict in predict_justSuc:
        take_profit_target_qs = TakeProfitTarget.objects.filter(post=predict.post, active=True).order_by('-index').first()
        if take_profit_target_qs:
            t += (take_profit_target_qs.profit or 0)
    rs = list(results)
    rs.append({
        'status__name': 'FAILED WITH PROFIT (JUST SUCCESS)',
        'total_profit': t,
        'count': len(predict_justSuc)
    })

    result_dict = {}
    for item in rs:
        key = item['status__name']
        profit_count = {'total_profit': item['total_profit'], 'count': item['count']}
        result_dict[key] = profit_count

    return JsonResponse(result_dict)


def tp_index_chart(request):
 
    return JsonResponse(tp_index_stat(request))

# settings
@login_required(login_url="login")
def get_settings(request):
    setting = SettingConfig.objects.get(id=1)
    return render(request, "Settings/index.html", {"setting": setting})


@login_required(login_url="login")
def update_settings(request):
    settings = SettingConfig.objects.get(id=1)
    max_leverage_param = float(request.POST.get("max_leverage"))
    leverage_effect_param = bool(request.POST.get("leverage_effect"))
    allow_channels_set_order_param = bool(request.POST.get("allow_channels"))
    max_entry_money_param = float(request.POST.get("max_entry_money"))

    settings.max_leverage = max_leverage_param
    settings.leverage_effect = leverage_effect_param
    settings.allow_channels_set_order = allow_channels_set_order_param
    settings.max_entry_money = max_entry_money_param
    settings.save()
    return redirect("Panel:settings")


# statistic
@login_required(login_url="login")
def get_statistic(request):
    positions = PositionSide.objects.all()
    channels = Channel.objects.all()
    postStatuses = PostStatus.objects.all()
    symbols = Symbol.objects.all()
    tp_index_profits = tp_index_stat(request)['profits']
    
    position_param = request.GET.get("position")
    channel_param = request.GET.get("channel")
    dateTo_param = request.GET.get("dateTo")
    dateFrom_param = request.GET.get("dateFrom")
    symbol_param = request.GET.get("symbol")

    
    query_filters = {}
    if channel_param:
        query_filters['post__channel__channel_id'] = channel_param 
    if position_param:
        query_filters['position__name'] = position_param
    if dateTo_param:
        query_filters['date__lte'] = dateTo_param
    if dateFrom_param:
        query_filters['date__gte'] = dateFrom_param
    if symbol_param:
        query_filters['symbol__name'] = symbol_param
    # print(query_filters)
    # try:
    results = Predict.objects.filter(
    **query_filters
    ).values('status__name').annotate(
        total_profit=Sum(F('profit')),
        count=Count('profit'),
    )
    
    predict_failed_justSuc = Predict.objects.filter(status__name="FAILED WITH PROFIT",**query_filters)
    t = 0
    for predict in predict_failed_justSuc:
        tp = TakeProfitTarget.objects.filter(post=predict.post, active=True).order_by('-index').first()
        # print(predict.symbol.name, int(tp.index)+1)
        if tp:
            # total_profit = (((tp.profit or 0)/100) +  1) * 100
            t += (tp.profit or 0)
    rs = list(results)

    rs.append({
        'status__name': 'FAILED WITH PROFIT (JUST SUCCESS)',
        'total_profit': t,
        'count': len(predict_failed_justSuc)
    })


    result_dict = {}
    for st in postStatuses:
        profit_count = {'total_profit': 0, 'count': 0}
        result_dict[st.name] = profit_count
    
    for item in rs:
        key = item['status__name']
        profit_count = {'total_profit': item['total_profit'], 'count': item['count']}
        result_dict[key] = profit_count
    
    # print(result_dict)
    criteria = {}
    
    criteria['win_count'] = result_dict['SUCCESS']['count'] + result_dict['FULLTARGET']['count']
    criteria['win_count_just_success'] = criteria['win_count'] + result_dict['FAILED WITH PROFIT (JUST SUCCESS)']['count']
    criteria['loss_count'] = result_dict['FAILED']['count'] + result_dict['FAILED WITH PROFIT']['count']
    criteria['loss_count_without_success'] = result_dict['FAILED']['count']
    criteria['total'] = criteria['win_count'] + criteria['loss_count'] + result_dict['PENDING']['count'] + result_dict['CANCELED']['count']
    
    criteria['win_rate'] = criteria['win_count']/criteria['total'] if criteria['total'] else 0
    criteria['win_rate_just_success'] = criteria['win_count_just_success']/criteria['total'] if criteria['total'] else 0
    
    criteria['loss_rate'] = criteria['loss_count']/criteria['total'] if criteria['total'] else 0
    criteria['loss_rate_without_success'] = criteria['loss_count_without_success']/criteria['total'] if criteria['total'] else 0
    
    criteria['gross_profit'] = result_dict['SUCCESS']['total_profit'] + result_dict['FULLTARGET']['total_profit']
    criteria['gross_profit_just_success'] = criteria['gross_profit'] + result_dict['FAILED WITH PROFIT (JUST SUCCESS)']['total_profit']

    criteria['gross_loss'] = result_dict['FAILED']['total_profit'] + result_dict['FAILED WITH PROFIT']['total_profit']
    criteria['gross_loss_without_success'] = result_dict['FAILED']['total_profit'] 

    criteria["average_win"] = criteria['gross_profit']/criteria['win_count'] if criteria['win_count'] else 0
    criteria["average_win_just_success"] = criteria['gross_profit_just_success']/criteria['win_count_just_success'] if criteria['win_count_just_success'] else 0

    criteria["average_loss"] = criteria['gross_loss']/criteria['loss_count'] if criteria['loss_count'] else 0
    criteria["average_loss_without_success"] = criteria['gross_loss_without_success']/criteria['loss_count_without_success'] if criteria['loss_count_without_success'] else 0

    criteria["expectancy"] = (criteria['win_rate']* criteria["average_win"])-(abs(criteria['loss_rate']*criteria["average_loss"]))
    criteria["expectancy_just_success"] = (criteria['win_rate_just_success']* criteria["average_win_just_success"])-(abs(criteria['loss_rate_without_success']*criteria["average_win_just_success"]))

    criteria["profit_factor"] = criteria['gross_profit']/criteria['gross_loss'] if criteria['gross_loss'] else 0
    criteria["profit_factor_just_success"] = criteria['gross_profit_just_success']/criteria['gross_loss_without_success'] if criteria['gross_loss_without_success'] else 0
    # criteria["profit_factor1"] = (criteria['win_rate']* criteria["average_win"])/(criteria['loss_rate']*criteria["average_loss"])

    criteria["payoff_ratio"] = criteria["average_win"]/criteria["average_loss"] if criteria['average_loss'] else 0
    criteria["payoff_ratio_just_success"] = criteria["average_win_just_success"]/criteria["average_loss_without_success"] if criteria['average_loss_without_success'] else 0
    tp_index_profits_array = [
        {'name': key, 'profit': value['profit'], 'count': value['count']} 
        for key, value in tp_index_profits.items()
    ]
    return render(request, "Statistic/index.html", {"symbols": symbols, "positions": positions, "channels": channels, "results": rs, "query_filters": query_filters, "criteria": criteria, "tp_index_profits_array": tp_index_profits_array})

    # except:
    #    return render(request, "Statistic/index.html", {"positions": positions, "channels": channels, "results": {}, "query_filters": query_filters, "criteria": {}})
  
   
    


async def set_phone_number(phone_number,token):
    config = dotenv_values(".env")

    api_id = config["api_id"]
    api_hash = config["api_hash"]

    username = config["username"]
    print(1)
    client = TelegramClient(username, api_id, api_hash)
    print(2)
    # await client.start()
    await client.connect()
    print( client._phone_code_hash)
    print(3)
    # Ensure you're authorized
    if not await client.is_user_authorized():
        print(4)
        if not token:
            await client.send_code_request(phone_number)
            print(phone_number)
            print(5)
        elif token:
            print(6)
            try:
                print(7)
                await client.send_code_request(phone_number)
                await client.sign_in(phone_number,token)
                print(8)
            except SessionPasswordNeededError:
                await client.sign_in(password=input('Password: '))
                
            print(9)
    print(10)
            
    # me = await client.get_me()

@login_required(login_url="login")
def getPhoneNumberAndCode(request):
    phone_number_param = request.POST.get("phone_number")
    token_param = request.POST.get("token")
    
    if phone_number_param:
        print(11)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(set_phone_number(phone_number_param,token_param))
    return render(request, "test.html", {"phone_number": phone_number_param})