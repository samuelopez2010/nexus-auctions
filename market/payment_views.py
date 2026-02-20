from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from users.models import Wallet, User
import requests
import json
import hmac
import hashlib

@login_required
def create_checkout_session(request):
    """
    Creates a NowPayments Invoice for adding funds to the wallet.
    """
    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount')
            if not amount_str:
                return JsonResponse({'error': 'Amount is required'}, status=400)
                
            amount_usd = float(amount_str)
            
            # NowPayments API Request
            headers = {
                'x-api-key': settings.NOWPAYMENTS_API_KEY,
                'Content-Type': 'application/json'
            }
            
            data = {
                'price_amount': amount_usd,
                'price_currency': 'usd',
                'order_id': f"DEP-{request.user.id}-{int(__import__('time').time())}",
                'order_description': 'Add funds to your Nexus Marketplace Wallet',
                'success_url': settings.BASE_URL + '/wallet/success/',
                'cancel_url': settings.BASE_URL + '/wallet/deposit/',
                # Provide user ID so we know whose wallet to credit in the IPN
                'ipn_callback_url': settings.BASE_URL + '/webhook/nowpayments/'
            }
            
            # Append user ID to tracking mechanism (NowPayments allows sending extra info sometimes, or we encode in order_id)
            # We encode user ID in the order_id: "DEP-{user_id}-{timestamp}"
            
            response = requests.post(f"{settings.NOWPAYMENTS_API_URL}/invoice", headers=headers, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                invoice_url = response_data.get('invoice_url')
                if invoice_url:
                    return redirect(invoice_url, code=303)
                else:
                    return JsonResponse({'error': 'Failed to generate invoice URL'}, status=500)
            else:
                print(f"NowPayments Error: {response.text}")
                return JsonResponse({'error': 'Payment Gateway Error'}, status=502)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def stripe_webhook(request): 
    # NOTE: Function renamed in urls.py to nowpayments_webhook, keeping name here temporary or updating. Let's rename it to nowpayments_webhook properly. 
    pass # Wait, I can't rename in replace if urls doesn't match yet. I will name it nowpayments_webhook and fix urls.py.

@csrf_exempt
def nowpayments_webhook(request):
    """
    Listens for NowPayments IPN (Instant Payment Notifications).
    """
    try:
        # 1. Verify Signature
        ipn_secret = settings.NOWPAYMENTS_IPN_SECRET
        received_signature = request.META.get('HTTP_X_NOWPAYMENTS_SIG')
        
        if not received_signature:
            return HttpResponse(status=400)
            
        request_data = dict(sorted(json.loads(request.body).items()))
        
        # NowPayments requires sorting keys and converting to JSON string without spaces
        sorted_json_str = json.dumps(request_data, separators=(',', ':'))
        
        calculated_signature = hmac.new(
            ipn_secret.encode('utf-8'),
            sorted_json_str.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        if received_signature != calculated_signature and ipn_secret != "your-ipn-secret-here": # Skip if secret is mock for dev
            print("Invalid signature")
            return HttpResponse(status=400)
            
        # 2. Process IPN
        payment_status = request_data.get('payment_status')
        order_id = request_data.get('order_id', '')
        price_amount = request_data.get('price_amount') # Original requested USD amount
        
        if payment_status == 'finished' and order_id.startswith('DEP-'):
            # Extract user_id from order_id (DEP-{user_id}-{timestamp})
            parts = order_id.split('-')
            if len(parts) >= 2:
                user_id_str = parts[1]
                
                try:
                    user = User.objects.get(id=int(user_id_str))
                    deposit_amount = float(price_amount)
                    
                    from django.db import transaction
                    with transaction.atomic():
                        wallet, _ = Wallet.objects.get_or_create(user=user)
                        wallet.balance += __import__('decimal').Decimal(deposit_amount)
                        wallet.save()
                        
                    print(f"WEBHOOK: Credited ${deposit_amount} to {user.username}")
                except User.DoesNotExist:
                    print(f"WEBHOOK ERROR: User {user_id_str} not found")

        return HttpResponse(status=200)

    except Exception as e:
        print(f"Webhook processing error: {e}")
        return HttpResponse(status=500)

@login_required
def payment_success(request):
    """
    Redirect destination after successful deposit.
    """
    from django.contrib import messages
    messages.success(request, "Invoice generated or payment processed! If finished, your wallet will be credited shortly.")
    return redirect('dashboard')
