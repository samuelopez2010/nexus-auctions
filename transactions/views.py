from rest_framework import viewsets, permissions
from django.db.models import Q
from .models import Transaction, Notification
from .serializers import TransactionSerializer, NotificationSerializer

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(Q(buyer=user) | Q(seller=user))

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .services import render_to_pdf

def download_invoice(request, transaction_id):
    transaction = get_object_or_404(Transaction, pk=transaction_id)
    # Security: Only buyer or seller can download
    if request.user != transaction.buyer and request.user != transaction.seller:
        return HttpResponse("Unauthorized", status=401)
        
    pdf = render_to_pdf('transactions/invoice.html', {'transaction': transaction})
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Invoice_{transaction.id}.pdf"
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response
    return HttpResponse("Not Found", status=404)
