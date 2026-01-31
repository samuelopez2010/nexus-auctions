from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import Product, Bid
from transactions.models import Transaction
import logging

logger = logging.getLogger(__name__)

@shared_task
def close_expired_auctions():
    """
    Periodic task to close auctions that have passed their end time.
    """
    now = timezone.now()
    # Find active auctions that have expired
    expired_products = Product.objects.filter(
        is_active=True,
        sales_type='AUCTION',
        auction_end_time__lte=now
    )

    count = 0
    for product in expired_products:
        with transaction.atomic():
            # Lock the row to prevent race conditions
            product = Product.objects.select_for_update().get(id=product.id)
            
            # Double check status after lock
            if not product.is_active:
                continue

            # Determine winner
            highest_bid = product.bids.order_by('-amount').first()
            
            if highest_bid:
                # Create Transaction
                # Use get_or_create to prevent duplicate transactions if task runs twice
                Transaction.objects.get_or_create(
                    product=product,
                    defaults={
                        'buyer': highest_bid.bidder,
                        'seller': product.seller,
                        'amount': highest_bid.amount,
                        'status': 'PENDING'
                    }
                )
                logger.info(f"Auction {product.id} closed. Winner: {highest_bid.bidder.username} - ${highest_bid.amount}")
                logger.info(f"Auction {product.id} closed. Winner: {highest_bid.bidder.username} - ${highest_bid.amount}")
                
                # Email Winner
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject=f"You Won! {product.title}",
                        message=f"Congratulations! You won the auction for '{product.title}' with a bid of ${highest_bid.amount}.\n\nPlease complete your payment here: http://localhost:8000/checkout/{product.id}/",
                        from_email=None,
                        recipient_list=[highest_bid.bidder.email],
                        fail_silently=True
                    )
                    
                    # Email Seller
                    send_mail(
                        subject=f"Item Sold: {product.title}",
                        message=f"Great news! Your item '{product.title}' has been sold for ${highest_bid.amount} to {highest_bid.bidder.username}.",
                        from_email=None,
                        recipient_list=[product.seller.email],
                        fail_silently=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send auction result emails: {e}")

            else:
                logger.info(f"Auction {product.id} closed with no bids.")
                # Email Seller (Unsold)
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject=f"Auction Ended: {product.title}",
                        message=f"Your auction for '{product.title}' has ended with no bids.",
                        from_email=None,
                        recipient_list=[product.seller.email],
                        fail_silently=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send unsold email: {e}")

            # Close the product
            product.is_active = False
            product.save()
            count += 1
    
    return f"Closed {count} auctions."
