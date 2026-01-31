from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import timedelta
from .models import Product, Bid

class BidService:
    @staticmethod
    @transaction.atomic
    def place_bid(product: Product, user, amount):
        """
        Places a bid on a product.
        Handles validation, concurrency locking, and sniper protection.
        """
        # Lock the product row for update to prevent race conditions
        product = Product.objects.select_for_update().get(id=product.id)

        # 1. Validation
        if not product.is_active:
            raise ValidationError("This auction is not active.")
        
        if product.sales_type == 'DIRECT':
            raise ValidationError("This product is for direct sale only.")
            
        if product.auction_end_time and timezone.now() > product.auction_end_time:
            raise ValidationError("This auction has ended.")

        # Check minimum bid
        min_bid = product.current_highest_bid + 1.00 # Minimum increment $1 (configurable)
        if product.current_highest_bid == 0:
            min_bid = product.initial_price if product.initial_price else 1.00

        if amount < min_bid:
            raise ValidationError(f"Bid must be at least {min_bid}")

        if user == product.seller:
            raise ValidationError("You cannot bid on your own product.")

        # 3.1 Notify Previous Bidder (Outbid)
        from django.core.mail import send_mail
        last_bid = Bid.objects.filter(product=product).order_by('-amount').first()
        if last_bid:
            previous_bidder = last_bid.bidder
            # Ensure we don't spam if the user outbids themselves (rare but possible)
            if previous_bidder != user:
                try:
                    send_mail(
                        subject=f"Outbid Alert: {product.title}",
                        message=f"You have been outbid on '{product.title}'.\nThe new highest bid is ${amount}.\n\nGo to product: http://localhost:8000/product/{product.id}/",
                        from_email=None,
                        recipient_list=[previous_bidder.email],
                        fail_silently=True 
                    )
                except Exception as e:
                    print(f"Failed to send outbid email: {e}")

        # 2. Create Bid
        Bid.objects.create(
            bidder=user,
            product=product,
            amount=amount
        )

        # 3. Update Product State
        product.current_highest_bid = amount
        
        # 4. Sniper Protection Check
        # If bid is placed in the last 30 seconds, extend by 1 minute
        if product.auction_end_time:
            time_remaining = product.auction_end_time - timezone.now()
            if time_remaining < timedelta(seconds=30):
                product.auction_end_time += timedelta(minutes=1)
                # TODO: Notify users about extension
        
        product.save()

        return product
