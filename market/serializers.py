from rest_framework import serializers
from .models import Category, Product, ProductImage, Bid
from users.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order']

class BidSerializer(serializers.ModelSerializer):
    bidder_name = serializers.ReadOnlyField(source='bidder.username')
    
    class Meta:
        model = Bid
        fields = ['id', 'bidder', 'bidder_name', 'amount', 'timestamp']
        read_only_fields = ['bidder', 'timestamp']

class ProductSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    bids = BidSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'category', 'category_id', 'title', 'description', 
            'condition', 'location', 'sales_type', 'initial_price', 'buy_now_price',
            'current_highest_bid', 'reserve_price', 'auction_end_time', 'is_active',
            'created_at', 'images', 'bids'
        ]
        read_only_fields = ['seller', 'current_highest_bid', 'is_active', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        product = Product.objects.create(seller=user, **validated_data)
        return product
