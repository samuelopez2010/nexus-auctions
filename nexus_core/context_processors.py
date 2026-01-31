from transactions.models import Notification

def global_context(request):
    context = {}
    if request.user.is_authenticated:
        context['unread_notifications_count'] = Notification.objects.filter(user=request.user, read=False).count()
        if hasattr(request.user, 'wallet'):
             context['wallet_balance'] = request.user.wallet.balance
        else:
             context['wallet_balance'] = 0.00
    return context
