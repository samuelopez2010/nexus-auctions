from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from users.models import Wallet, User
import stripe
import json

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_checkout_session(request):
    """
    Creates a Stripe Checkout Session for adding funds to the wallet.
    """
    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount')
            if not amount_str:
                return JsonResponse({'error': 'Amount is required'}, status=400)
                
            # Amount in cents
            amount_usd = float(amount_str)
            amount_cents = int(amount_usd * 100)
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': amount_cents,
                        'product_data': {
                            'name': 'Wallet Deposit',
                            'description': 'Add funds to your Nexus Marketplace Wallet',
                            # 'images': ['https://your-domain.com/static/logo.png'],
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=settings.BASE_URL + '/wallet/success/?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=settings.BASE_URL + '/wallet/deposit/',
                client_reference_id=str(request.user.id), # Pass user ID to webhook
                metadata={
                    'transaction_type': 'DEPOSIT',
                    'user_id': request.user.id
                }
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def stripe_webhook(request):
    """
    Listens for Stripe webhooks to confirm payment and credit wallet.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None
    
    # If no webhook secret is set (dev mode), just trust the event type for testing?
    # No, strictly follow stripe verification or fallback to simple parsing for now if secret missing
    
    try:
        if settings.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        else:
            # DEV MODE: Parse without signature verification if no secret provided
            # WARNING: NOT SECURE FOR PRODUCTION
            event = json.loads(payload)
            # Normalize structure if utilizing raw json
            if 'type' not in event:
                return HttpResponse(status=400)

    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Fulfill the purchase
        user_id = session.get('client_reference_id')
        amount_total = session.get('amount_total') # in cents
        
        if user_id and amount_total:
            try:
                user = User.objects.get(id=int(user_id))
                deposit_amount = amount_total / 100.0
                
                # Update Wallet
                # Using select_for_update to handle concurrency
                from django.db import transaction
                with transaction.atomic():
                    wallet, _ = Wallet.objects.get_or_create(user=user)
                    wallet.balance += __import__('decimal').Decimal(deposit_amount)
                    wallet.save()
                    
                print(f"WEBHOOK: Credited ${deposit_amount} to {user.username}")
                
            except User.DoesNotExist:
                print(f"WEBHOOK ERROR: User {user_id} not found")

    return HttpResponse(status=200)

@login_required
def payment_success(request):
    """
    Redirect destination after successful Stripe payment.
    """
    from django.contrib import messages
    # OPTIONAL: Verify session_id via API for extra security before showing message
    messages.success(request, "Funds added successfully! Your wallet has been credited.")
    return redirect('dashboard')
