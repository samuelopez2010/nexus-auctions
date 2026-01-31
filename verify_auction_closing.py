
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus_core.settings')
django.setup()


from users.models import User
from market.models import Product, Bid, Category
from transactions.models import Transaction
from market.tasks import close_expired_auctions

def verify():
    print("Setting up test data...")
    # Clean up leftovers
    Product.objects.filter(title="Test Auction Item").delete()
    
    # Create Users
    seller, _ = User.objects.get_or_create(username="seller_bot", email="seller@bot.com")
    buyer, _ = User.objects.get_or_create(username="buyer_bot", email="buyer@bot.com")
    
    # Create Category
    category, _ = Category.objects.get_or_create(name="Test Category", slug="test-category")

    # Create Expired Auction
    product = Product.objects.create(
        seller=seller,
        category=category,
        title="Test Auction Item",
        description="Testing auto-close",
        initial_price=10.00,
        sales_type='AUCTION',
        is_active=True,
        auction_end_time=timezone.now() - timedelta(minutes=1) # Ended 1 min ago
    )
    
    # Place Bid
    Bid.objects.create(
        bidder=buyer,
        product=product,
        amount=15.00
    )
    product.current_highest_bid = 15.00
    product.save()
    
    print(f"Created expired auction {product.id} with bid $15.00")
    
    # Run Task
    print("Running close_expired_auctions task...")
    result = close_expired_auctions()
    print(f"Task Result: {result}")
    
    # Verify
    product.refresh_from_db()
    if not product.is_active:
        print("PASS: Product is now inactive.")
    else:
        print("FAIL: Product is still active.")
        
    tx = Transaction.objects.filter(product=product).first()
    if tx:
        print(f"PASS: Transaction created for {tx.buyer.username} - ${tx.amount} status={tx.status}")
    else:
        print("FAIL: No transaction created.")

if __name__ == "__main__":
    verify()
