from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('USED', 'Used'),
        ('REFURBISHED', 'Refurbished'),
    ]
    SALES_TYPE_CHOICES = [
        ('DIRECT', 'Direct Sale Only'),
        ('AUCTION', 'Auction Only'),
        ('HYBRID', 'Hybrid (Auction + Buy Now)'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    title = models.CharField(max_length=255)
    description = models.TextField()
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    location = models.CharField(max_length=100)
    
    # Hybridization Fields
    sales_type = models.CharField(max_length=20, choices=SALES_TYPE_CHOICES, default='DIRECT')
    initial_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Starting price for direct sale or auction start")
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    current_highest_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reserve_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Minimum price to sell in auction")
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SOLD', 'Sold'),
        ('EXPIRED', 'Expired'),
        ('PENDING', 'Pending Payment'),
    ]
    
    auction_end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_active = models.BooleanField(default=True) # Keeping for backward compatibility temporarily
    is_variable_price = models.BooleanField(default=False, help_text="If true, price defaults to 0 and user selects amount.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Bid(models.Model):
    bidder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bids')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} on {self.product.title} by {self.bidder.username}"
