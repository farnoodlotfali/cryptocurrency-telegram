from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
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
    PositionSide,
    StopLoss
)
from django.db.models import Count, Sum, Max, Case, When, IntegerField, FloatField, Value, CharField, F
from Shared.Constant import PostStatusValues
from django.db.models.functions import TruncMonth

LOGIN_PAGE_URL = "/panel/login"

# HTTP Error 404
@login_required(login_url=LOGIN_PAGE_URL)
def custom_404_view(request, exception):
    return render(request, '404.html', status=404)


@login_required(login_url=LOGIN_PAGE_URL)
def home(request):
    channels = Channel.objects.all()
    predicts = Predict.objects.all()
    posts = Post.objects.all()
    Markets = Market.objects.all()
    predicts_status = predicts.values('status__name').annotate(count=Count('id')).order_by('status__name')
    
    return render(request, "Home/home.html", {"channels": channels,
                                              "predicts": predicts,
                                              "predicts_status": predicts_status,
                                              "posts": posts,
                                              "Markets": Markets})

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
@login_required(login_url=LOGIN_PAGE_URL)
def get_symbols(request):
    symbols = Symbol.objects.all()
    return render(request, "Symbol/index.html", {"symbols": symbols})


# markets
@login_required(login_url=LOGIN_PAGE_URL)
def get_markets(request):
    markets = Market.objects.all()
    return render(request, "Market/index.html", {"markets": markets})


# predicts
@login_required(login_url=LOGIN_PAGE_URL)
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
   
    return render(
        request,
        "Predict/index.html",
        {"predicts": predicts,
        "symbols": symbols,
        "symbol_param": symbol_param,
        "channels": channels,
        "channel_param": channel_param,
        },
    )


# channels
@login_required(login_url=LOGIN_PAGE_URL)
def channel_list(request):
    channels = Channel.objects.all()
    return render(request, "Channel/channelList.html", {"channels": channels})


# change channel trade
@login_required(login_url=LOGIN_PAGE_URL)
def change_channel_trade(request, channel_id):
    channel = Channel.objects.get(channel_id=channel_id)
    channel.can_trade = not channel.can_trade
    channel.save()
    return redirect("Panel:channel_list")


# channel detail
@login_required(login_url=LOGIN_PAGE_URL)
def channel_detail(request, channel_id):
    channel = get_object_or_404(Channel, channel_id=channel_id)
    predicts = Predict.objects.filter(post__channel=channel)
    success_predicts = predicts.filter(profit__gt=0)
    failed_predicts = predicts.filter(profit__lt=0)
    return render(request, "Channel/channelDetail.html", { "channel": channel,
                                                          "predicts": predicts,
                                                          "success_predicts": success_predicts,
                                                          "failed_predicts": failed_predicts,
                                                          })


# posts list
@login_required(login_url=LOGIN_PAGE_URL)
def post_list(request):
    posts = Post.objects.all().order_by("-id")
    return render(request, "Post/postList.html", {"posts": posts})


# predict detail
@login_required(login_url=LOGIN_PAGE_URL)
def predict_detail(request, post_id):
    post = Post.objects.get(pk=post_id)

    related_posts = Post.objects.filter(reply_to_msg_id=post.message_id)

    predict = None
    entries = None
    take_profits = None
    stoploss = None
    if post.is_predict_msg:

        predict = Predict.objects.get(post=post)
        entries = EntryTarget.objects.filter(predict=predict)
        take_profits = TakeProfitTarget.objects.filter(predict=predict)
        stoploss = StopLoss.objects.get(predict=predict)



    return render(
        request,
        "Predict/predictDetail.html",
        {
            "post": post,
            "related_posts": related_posts,
            "predict": predict,
            "entries": entries,
            "take_profits": take_profits,
            "stoploss": stoploss,
        },
    )


# change predict status
@login_required(login_url=LOGIN_PAGE_URL)
def change_predict_status(request, predict_id, status):
    try:
        predict = Predict.objects.get(pk=predict_id)
        newStatus = PostStatus.objects.get(name=status)
        predict.status = newStatus
        predict.save()
    except:
        print("error")

    return redirect("Panel:predict")


# settings
@login_required(login_url=LOGIN_PAGE_URL)
def get_settings(request):
    setting = SettingConfig.objects.get(id=1)
    return render(request, "Settings/index.html", {"setting": setting})

# update settings
@login_required(login_url=LOGIN_PAGE_URL)
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

# statistic of predicts
@login_required(login_url=LOGIN_PAGE_URL)
def get_predicts_stat(request):
    positions = PositionSide.objects.all()
    channels = Channel.objects.all()
    symbols = Symbol.objects.all()
    # ********************************************************
    
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

    # ********************************************************


    status_status = Predict.objects.filter(**query_filters).values('status__name').annotate(total_profit=Sum('profit'), count=Count('id')).order_by('status__name')
   

    # ********************************************************

    predicts_result = Predict.objects.filter(**query_filters).aggregate(
            gross_loss=Sum(
                Case(
                    When(status__name__in=[PostStatusValues.FAILED_WITH_PROFIT.value, PostStatusValues.FAILED.value], then='profit'),
                    output_field=FloatField()
                )
            ),
            loss_count=Count(
                Case(
                    When(status__name__in=[PostStatusValues.FAILED_WITH_PROFIT.value, PostStatusValues.FAILED.value], then=1),
                    output_field=IntegerField()
                )
            ),
            gross_profit=Sum(
                Case(
                    When(status__name__in=[PostStatusValues.SUCCESS.value, PostStatusValues.FULLTARGET.value], then='profit'),
                    output_field=FloatField()
                )
            ),
            win_count=Count(
                Case(
                    When(status__name__in=[PostStatusValues.SUCCESS.value, PostStatusValues.FULLTARGET.value], then=1),
                    output_field=IntegerField()
                )
            ),
            total_gross=Sum('profit', output_field=FloatField()), 
            total_count=Count('id', output_field=IntegerField()) 
        )

    gross_loss = predicts_result['gross_loss']
    loss_count = predicts_result['loss_count']
    gross_profit = predicts_result['gross_profit']
    win_count = predicts_result['win_count']
    total_count = predicts_result['total_count']
    total_gross = predicts_result['total_gross']

    loss_rate = loss_count/total_count if total_count else 0
    win_rate = win_count/total_count if total_count else 0
    average_loss = gross_loss/loss_count if loss_count else 0
    average_win = gross_profit/win_count if win_count else 0
    expectancy = (win_rate * average_win)-(abs(loss_rate * average_loss))
    profit_factor =  abs(gross_profit/gross_loss if gross_loss else 0)
    payoff_ratio = abs(average_win/average_loss if average_loss else 0)
    # ********************************************************

    tp_query_filters = {}
    if channel_param:
        tp_query_filters['predict__post__channel__channel_id'] = channel_param 
    if position_param:
        tp_query_filters['predict__position__name'] = position_param
    if dateTo_param:
        tp_query_filters['predict__date__lte'] = dateTo_param
    if dateFrom_param:
        tp_query_filters['predict__date__gte'] = dateFrom_param
    if symbol_param:
        tp_query_filters['predict__symbol__name'] = symbol_param

    tp_query = TakeProfitTarget.objects.filter(active=True, **tp_query_filters).values('predict_id').annotate(tp_index=Count('id'), max_profit=Max('profit'))
    tp_query_FAILED_WITH_PROFIT = TakeProfitTarget.objects.filter(active=True, predict__status__name=PostStatusValues.FAILED_WITH_PROFIT.value, **tp_query_filters).values('predict_id').annotate(tp_index=Count('id'), max_profit=Max('profit'))
    
    def findTpResult(queries):
        tp_result = {}
        for entry in queries:
            tp_index = entry['tp_index']
            max_profit = entry['max_profit']
            if tp_index not in tp_result:
                tp_result[tp_index] = {'count': 0, 'total_profit': 0}
            tp_result[tp_index]['count'] += 1
            tp_result[tp_index]['total_profit'] += max_profit

        
        tp_result = [
            {'tp_index': tp_index, 'count': data['count'], 'total_profit': data['total_profit']}
            for tp_index, data in sorted(tp_result.items())
        ]
        return tp_result
    
    tp_result_arrange = findTpResult(tp_query)
    tp_result_arrange_FAILED_WITH_PROFIT = findTpResult(tp_query_FAILED_WITH_PROFIT)
    # ********************************************************
    
    
    return render(request, "Statistic/index.html", {"symbols": symbols,
                                                    "positions": positions,
                                                    "channels": channels,
                                                    "status_status": status_status,
                                                    "query_filters": query_filters,
                                                    "tp_status": tp_result_arrange,
                                                    "tp_query_FAILED_WITH_PROFIT": tp_result_arrange_FAILED_WITH_PROFIT,
                                                    "total_count": total_count,
                                                    "total_gross": total_gross,
                                                    "gross_loss": gross_loss,
                                                    "loss_count": loss_count,
                                                    "gross_profit": gross_profit,
                                                    "win_count": win_count,
                                                    "loss_rate": loss_rate,
                                                    "win_rate": win_rate,
                                                    "average_loss": average_loss,
                                                    "average_win": average_win,
                                                    "expectancy": expectancy,
                                                    "profit_factor": profit_factor,
                                                    "payoff_ratio": payoff_ratio,
                                                    })

    # except:
    #    return render(request, "Statistic/index.html", {"positions": positions, "channels": channels, "results": {}, "query_filters": query_filters, "criteria": {}})
  
   
# statistic of channels
@login_required(login_url=LOGIN_PAGE_URL)
def get_channels_stat(request):

    channel_predict = Channel.objects.filter(post__predict__status__name__in=[PostStatusValues.FAILED.value, PostStatusValues.FAILED_WITH_PROFIT.value, PostStatusValues.SUCCESS.value, PostStatusValues.FULLTARGET.value]).annotate(status_group=Case(
        When(post__predict__status__name__in=[PostStatusValues.FAILED.value, PostStatusValues.FAILED_WITH_PROFIT.value], then=Value('FAILED_GROUP')),
        When(post__predict__status__name__in=[PostStatusValues.SUCCESS.value, PostStatusValues.FULLTARGET.value], then=Value('SUCCESS_GROUP')),
        output_field=CharField(),
    ),
        predict_count=Count('post__predict', distinct=True),
    ).values('channel_id', 'name', 'status_group', 'predict_count').order_by('channel_id', 'status_group')

    channel_predict_total = Predict.objects.filter(post__channel__isnull=False).annotate(channel_id=F('post__channel__channel_id')).values('channel_id').annotate(total_count=Count('id'))
        
    channel_predict_result = {}

    for entry in channel_predict:
        channel_id = entry['channel_id']
        if channel_id not in channel_predict_result:
            channel_predict_result[channel_id] = {
                'channel_id': channel_id,
                'name': entry['name'], 
                'FAILED_GROUP': 0,
                'SUCCESS_GROUP': 0
            }
        
        if entry['status_group'] == 'FAILED_GROUP':
            channel_predict_result[channel_id]['FAILED_GROUP'] += entry['predict_count']
        elif entry['status_group'] == 'SUCCESS_GROUP':
            channel_predict_result[channel_id]['SUCCESS_GROUP'] += entry['predict_count']

    for entry in channel_predict_total:
        channel_id = entry['channel_id']
        if channel_id in channel_predict_result:
            channel_predict_result[channel_id]['total_count'] = entry['total_count']
            channel_predict_result[channel_id]['win_rate'] = channel_predict_result[channel_id]['SUCCESS_GROUP']/entry['total_count']
            channel_predict_result[channel_id]['loss_rate'] = channel_predict_result[channel_id]['FAILED_GROUP']/entry['total_count']

    channel_predict_result_final = list(channel_predict_result.values())
    print(channel_predict_result_final)

    # ********************************************************


    return render(request, "Statistic/channel-stat.html", {'stat_per_month': channel_stat_per_month(request),
                                                           'stat_total': channel_stat_total(request),
                                                            "channel_predict_result_final": channel_predict_result_final,
                                                           })

# total statistic of channels
def channel_stat_total(request):
    results = (
        Predict.objects
        .select_related('post__channel')
        .values('post__channel__name')
        .annotate(total_profit=Sum('profit'))
        .order_by('post__channel__name')
    )
    return results

def channel_stat_per_month(request):
    results = (
        Predict.objects
        .select_related('post__channel')
        .annotate(month=TruncMonth('date'))
        .values('post__channel__name', 'month')
        .annotate(total_profit=Sum('profit'))
        .order_by('month', 'post__channel__name')
    )
    return results

def channel_stat_per_month_chart(request):
    results_list = list(channel_stat_per_month(request))
    return JsonResponse(results_list, safe=False)

def channel_stat_total_chart(request):
    results_list = list(channel_stat_total(request))
    return JsonResponse(results_list, safe=False)

