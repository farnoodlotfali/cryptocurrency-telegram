from django import template
from Shared.Constant import PostStatusValues
from django.urls import reverse, NoReverseMatch

register = template.Library()

@register.simple_tag(takes_context=True)
def is_active(context, url_name):
    try:
        current_url = context['request'].path
        url = reverse(url_name)
        return 'active' if current_url == url else ''
    except NoReverseMatch:
        return ''
    
@register.filter(name='round_number')
def round_number(value, args):
    if not value:
        return ""
    precision = int(args)
    return round(value, precision)

@register.filter(name='abs_number')
def abs_number(value):
    if not value:
        return ""
    
    return abs(value)

@register.filter(name='status_color')
def status_color(status):
    if status == PostStatusValues.SUCCESS.value:
        return "text-lime" 
    elif status == PostStatusValues.FAILED.value or  status == PostStatusValues.CANCELED.value:
        return "text-danger" 
    elif status == PostStatusValues.FULLTARGET.value:
        return "text-green" 
    elif status == PostStatusValues.ERROR.value:
        return "text-maroon" 
    elif status == PostStatusValues.FAILED_WITH_PROFIT.value:
        return "text-orange" 
    elif status == PostStatusValues.PENDING.value:
        return "text-gray"
    elif status == PostStatusValues.WAIT_MANY_DAYS.value:
        return "text-yellow"