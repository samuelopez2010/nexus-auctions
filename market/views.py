from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer, BidSerializer
from .services import BidService
from django.core.exceptions import ValidationError

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'condition', 'sales_type', 'location']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'current_highest_bid', 'auction_end_time']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Custom filtering examples
        ending_soon = self.request.query_params.get('ending_soon')
        if ending_soon:
            queryset = queryset.order_by('auction_end_time')
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bid(self, request, pk=None):
        product = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
            updated_product = BidService.place_bid(product, request.user, amount)
            return Response(ProductSerializer(updated_product).data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'An error occurred'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def buy_now(self, request, pk=None):
        # Implementation for Buy Now would go here
        # Similar to bid, validation then Transaction creation
        return Response({'status': 'Buy Now feature in progress'})
