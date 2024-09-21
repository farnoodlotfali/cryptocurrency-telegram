# ## Ignore Same Signal
# if predict_status is "SUCCESS" or "PENDING", will remove it to check again

from datetime import timedelta
from asgiref.sync import sync_to_async
from PostAnalyzer.models import (
    EntryTarget,
    Predict,
    TakeProfitTarget,
    Symbol,
    Market,
    PositionSide,
    MarginMode,
)

async def findSameSignal(date, symbol: Symbol, market: Market, position: PositionSide, leverage: int, margin_mode: MarginMode, stoploss: float, TPs: list[float], entries: list[float], channel_id):
    two_day_ago = date - timedelta(seconds=172_800)
    
    predict_find = await sync_to_async(list)(Predict.objects.filter(
        symbol__name=symbol.name,
        market__name=market.name,
        position__name=position.name,
        margin_mode__name=margin_mode.name,
        leverage=int(leverage),
        stopLoss=float(stoploss),
        post__channel__channel_id=channel_id,
        # date__gte=two_day_ago
    ).select_related('post', 'status'))
    

    if predict_find:

        for item in predict_find:
            predict_post = item.post
            predict_status = item.status
            equal_entries = []
            equal_tps = []

            entries_find = await sync_to_async(list)(EntryTarget.objects.filter(post=predict_post))
            if len(entries_find) == len(entries):
                for i, entry in enumerate(entries_find):
                    if float(entry.value) == float(entries[i]):
                        equal_entries.append(entries[i])
            
            tps_find = await sync_to_async(list)(TakeProfitTarget.objects.filter(post=predict_post).order_by('index'))
            if len(tps_find) == len(TPs):
                for i, tp in enumerate(tps_find):
                    if float(tp.value) == float(TPs[i]):
                        equal_tps.append(TPs[i])
          
            if (len(equal_entries) == len(entries)) and (len(equal_tps) == len(TPs)):
                if predict_status.name == "SUCCESS" or predict_status.name == "PENDING":
                    await sync_to_async(item.delete)()
                    return False
                
                return True

    else:
        return False

    
