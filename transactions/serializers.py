from rest_framework import serializers
from .models import Transaction, Review, Dispute, Notification

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['buyer', 'seller', 'product', 'amount', 'status', 'transaction_date', 'invoice_file']

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['author', 'target_user', 'transaction', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['user', 'type', 'message', 'created_at']
