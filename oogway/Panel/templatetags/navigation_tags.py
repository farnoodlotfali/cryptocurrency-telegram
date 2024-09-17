from django import template
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
    if status == 'SUCCESS':
        return "text-lime" 
    elif status == 'FAILED' or  status == 'CANCELED':
        return "text-danger" 
    elif status == 'FULLTARGET':
        return "text-green" 
    elif status == 'ERROR':
        return "text-maroon" 
    elif status == 'FAILED WITH PROFIT':
        return "text-orange" 
    elif status == 'PENDING':
        return "text-gray"