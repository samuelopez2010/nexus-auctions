from django.conf import settings
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from users.models import Wallet, User
import requests
import json
import base64

def get_paypal_access_token():
    client_id = settings.PAYPAL_CLIENT_ID
    secret = settings.PAYPAL_SECRET
    mode = settings.PAYPAL_MODE
    
    base_url = "https://api-m.paypal.com" if mode == 'live' else "https://api-m.sandbox.paypal.com"
    auth_string = f"{client_id}:{secret}"
    auth_bytes = auth_string.encode('ascii')
    auth_base64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    response = requests.post(f"{base_url}/v1/oauth2/token", headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

@login_required
def create_checkout_session(request):
    """
    Creates a PayPal Order for adding funds to the wallet.
    """
    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount')
            if not amount_str:
                return JsonResponse({'error': 'Amount is required'}, status=400)
                
            amount_usd = float(amount_str)
            
            # PayPal API Request
            access_token = get_paypal_access_token()
            if not access_token:
                return JsonResponse({'error': 'Failed to authenticate with payment gateway'}, status=500)
                
            mode = settings.PAYPAL_MODE
            base_url = "https://api-m.paypal.com" if mode == 'live' else "https://api-m.sandbox.paypal.com"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            # Create Order payload
            order_data = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "reference_id": f"DEP_{request.user.id}_{int(__import__('time').time())}",
                        "description": "Deposit to Nexus Auctions Wallet",
                        "custom_id": str(request.user.id),
                        "amount": {
                            "currency_code": "USD",
                            "value": f"{amount_usd:.2f}"
                        }
                    }
                ],
                "application_context": {
                    "return_url": settings.BASE_URL + '/paypal/capture/',
                    "cancel_url": settings.BASE_URL + '/wallet/deposit/',
                    "user_action": "PAY_NOW"
                }
            }
            
            response = requests.post(f"{base_url}/v2/checkout/orders", headers=headers, json=order_data)
            
            if response.status_code in [200, 201]:
                order = response.json()
                # Find the approval URL to redirect the user
                for link in order.get('links', []):
                    if link.get('rel') == 'approve':
                        # Store order ID in session to verify later
                        request.session['paypal_order_id'] = order.get('id')
                        return redirect(link.get('href'), code=303)
                        
                return JsonResponse({'error': 'Approval URL not found in PayPal response'}, status=500)
            else:
                print(f"PayPal Order Error: {response.text}")
                return JsonResponse({'error': 'Payment Gateway Error'}, status=502)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
def paypal_capture(request):
    """
    Captures the PayPal order after the user approves it on PayPal's site.
    """
    order_id = request.GET.get('token')
    session_order_id = request.session.get('paypal_order_id')
    
    if not order_id or order_id != session_order_id:
        from django.contrib import messages
        messages.error(request, "Invalid or expired payment session.")
        return redirect('deposit_funds')
        
    try:
        access_token = get_paypal_access_token()
        mode = settings.PAYPAL_MODE
        base_url = "https://api-m.paypal.com" if mode == 'live' else "https://api-m.sandbox.paypal.com"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        # Capture the order
        response = requests.post(f"{base_url}/v2/checkout/orders/{order_id}/capture", headers=headers)
        
        if response.status_code in [200, 201]:
            capture_data = response.json()
            status = capture_data.get('status')
            
            if status == 'COMPLETED':
                # Get the custom_id which holds the user.id, and the amount
                purchase_units = capture_data.get('purchase_units', [])
                if purchase_units:
                    unit = purchase_units[0]
                    user_id_str = unit.get('custom_id')
                    
                    # Capture amount is inside payments.captures
                    captures = unit.get('payments', {}).get('captures', [])
                    if captures:
                        amount_value = captures[0].get('amount', {}).get('value')
                        
                        try:
                            user = User.objects.get(id=int(user_id_str))
                            deposit_amount = float(amount_value)
                            
                            # Update Wallet ensuring it belongs to the logged-in user
                            if user == request.user:
                                from django.db import transaction
                                with transaction.atomic():
                                    wallet, _ = Wallet.objects.get_or_create(user=user)
                                    wallet.balance += __import__('decimal').Decimal(deposit_amount)
                                    wallet.save()
                                    
                                print(f"PAYPAL CAPTURE: Credited ${deposit_amount} to {user.username}")
                                
                                # Clear session
                                if 'paypal_order_id' in request.session:
                                    del request.session['paypal_order_id']
                                
                                return redirect('payment_success')
                            else:
                                print(f"PAYPAL SECURITY: User mismatch. Captured {user_id_str} but logged in as {request.user.id}")
                        except User.DoesNotExist:
                            print(f"PAYPAL ERROR: User {user_id_str} not found in capture")
        
        # If we reach here, capture failed or wasn't COMPLETED
        print(f"PAYPAL CAPTURE FAILED: {response.text}")
        from django.contrib import messages
        messages.error(request, "Payment could not be captured. Please try again.")
        return redirect('deposit_funds')
        
    except Exception as e:
        print(f"Capture processing error: {e}")
        from django.contrib import messages
        messages.error(request, "An error occurred while processing your payment.")
        return redirect('deposit_funds')

@login_required
def payment_success(request):
    """
    Redirect destination after successful deposit.
    """
    from django.contrib import messages
    messages.success(request, "Invoice generated or payment processed! If finished, your wallet will be credited shortly.")
    return redirect('dashboard')
