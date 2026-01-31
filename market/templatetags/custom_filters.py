from django import template

register = template.Library()

@register.filter
def should_fire_confetti(message):
    tags = message.tags or ''
    text = message.message or ''
    if 'success' in tags:
        if 'purchased' in text or 'won' in text or 'Bid placed' in text:
            return True
    return False

from django.utils import timezone

@register.filter
def precise_time_left(end_time):
    if not end_time:
        return ""
    now = timezone.now()
    if end_time < now:
        return "00m 00s"
    
    remaining = end_time - now
    total_seconds = int(remaining.total_seconds())
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"

@register.filter
def is_expired(end_time):
    if not end_time:
        return False
    return end_time < timezone.now()

