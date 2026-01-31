from django.contrib import admin
from .models import Category, Product, ProductImage, Bid

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'seller', 'category', 'sales_type', 'current_highest_bid', 'is_active', 'auction_end_time']
    list_filter = ['sales_type', 'condition', 'is_active', 'category']
    search_fields = ['title', 'description', 'seller__username']
    inlines = [ProductImageInline]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['product', 'bidder', 'amount', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['product__title', 'bidder__username']
