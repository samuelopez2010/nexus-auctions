from django.contrib import admin
from .models import Transaction, Review, Dispute, Notification

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'product', 'amount', 'status', 'transaction_date']
    list_filter = ['status', 'transaction_date']
    search_fields = ['product__title', 'buyer__username', 'seller__username']

admin.site.register(Review)
admin.site.register(Dispute)
admin.site.register(Notification)
