from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Q, Sum
from .models import Product, Category, Bid, ProductImage
from users.models import User, Wallet
from .services import BidService
from django.core.exceptions import ValidationError
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from transactions.models import Transaction, Review

def home(request):
    # Base Query
    all_products = Product.objects.filter(status='ACTIVE')
    
    # 1. Search Query
    query = request.GET.get('q')
    if query:
        all_products = all_products.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    else:
        all_products = all_products.order_by('-created_at')

    # 2. Hero Product (Auction nearing end, exclude variable price)
    hero_product = all_products.filter(sales_type__in=['AUCTION', 'HYBRID'], is_variable_price=False).order_by('auction_end_time').first()

    # 3. Hot Auctions (Most urgent, excluding hero)
    if hero_product:
        hot_auctions = all_products.filter(sales_type__in=['AUCTION', 'HYBRID'], is_variable_price=False).exclude(id=hero_product.id).order_by('auction_end_time')[:4]
    else:
        hot_auctions = all_products.filter(sales_type__in=['AUCTION', 'HYBRID'], is_variable_price=False).order_by('auction_end_time')[:4]

    # 4. New Arrivals (Direct Buy)
    new_arrivals = all_products.filter(sales_type__in=['DIRECT', 'HYBRID'], is_variable_price=False).order_by('-created_at')[:4]
    
    # 5. Gift Cards (Featured)
    gift_cards = Product.objects.filter(status='ACTIVE', is_variable_price=True)[:2]

    # User Stats (Simplified)
    user_stats = {}
    if request.user.is_authenticated:
        user_stats['winning'] = Product.objects.filter(bids__bidder=request.user).distinct().count()
        user_stats['outbid'] = 0 # Placeholder

    # Get Categories for Sidebar
    categories = Category.objects.all()

    context = {
        'hero_product': hero_product,
        'hot_auctions': hot_auctions,
        'new_arrivals': new_arrivals,
        'featured_gift_cards': gift_cards,
        'user_stats': user_stats,
        'query': query,
        'categories': categories
    }
    return render(request, 'index.html', context)

def gift_cards(request):
    # Get all active gift cards
    cards = Product.objects.filter(status='ACTIVE', is_variable_price=True)
    
    # Simple filtering
    sort = request.GET.get('sort')
    if sort == 'newest':
        cards = cards.order_by('-created_at')
    
    return render(request, 'market/gift_cards.html', {'cards': cards})

def catalog(request):
    products = Product.objects.filter(status='ACTIVE')
    
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    conditions = request.GET.getlist('condition')
    sales_type = request.GET.get('sales_type') # AUCTION or DIRECT
    category_id = request.GET.get('category')
    
    if min_price: products = products.filter(initial_price__gte=min_price)
    if max_price: products = products.filter(initial_price__lte=max_price)
    if conditions: products = products.filter(condition__in=conditions)
    if sales_type: products = products.filter(sales_type=sales_type)
    if category_id: products = products.filter(category_id=category_id)
    
    # Sort
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_asc': products = products.order_by('initial_price')
    elif sort_by == 'price_desc': products = products.order_by('-initial_price')
    elif sort_by == 'urgent': products = products.filter(sales_type__in=['AUCTION', 'HYBRID']).order_by('auction_end_time')
    else: products = products.order_by('-created_at')
    
    # Get all categories for filter
    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'selected_category': int(category_id) if category_id else None,
        'selected_conditions': conditions, # Pass list for template check
        'selected_sales_type': sales_type,
        'selected_sort': sort_by,
        'min_price': min_price,
        'max_price': max_price,
    }
    
    return render(request, 'market/catalog.html', context)

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    # Mark all as read when viewing the page (simple implementation)
    # notifications.update(read=True) # Optional: uncomment if we want auto-mark-read
    return render(request, 'market/notifications.html', {'notifications': notifications})

from .forms import ProductForm
from transactions.models import Transaction, Notification
from django.utils import timezone

@login_required
def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            
            # Handle images (simplified for single upload in this example, or use formset)
            images = request.FILES.getlist('images')
            for img in images:
                ProductImage.objects.create(product=product, image=img)
                
            messages.success(request, "Listing created successfully!")
            return redirect('product_detail', pk=product.id)
    else:
        form = ProductForm()
    return render(request, 'market/create_product.html', {'form': form})

@login_required
def checkout(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        # 1. Determine Price
        # Check if we have a dynamic amount override (for Gift Cards)
        dynamic_amount = request.POST.get('final_amount')
        
        if product.is_variable_price and dynamic_amount:
            try:
                total_cost = Decimal(dynamic_amount)
                if total_cost <= 0: raise ValueError
            except:
                messages.error(request, "Invalid amount entered.")
                return redirect('product_detail', pk=pk)
        else:
            # Standard logic
            price_val = product.buy_now_price if product.buy_now_price else product.initial_price
            total_cost = Decimal(str(price_val))
        
        # 2. Usamos un bloque atómico: o se hace todo, o no se hace nada
        with transaction.atomic():
            # Asegurar billeteras (get_or_create es más limpio)
            buyer_wallet, _ = Wallet.objects.get_or_create(user=request.user)
            seller_wallet, _ = Wallet.objects.get_or_create(user=product.seller)
            
            # Refrescamos el balance desde la BD para evitar errores de caché
            if buyer_wallet.balance >= total_cost:
                # Deduct from Buyer
                buyer_wallet.balance -= total_cost
                buyer_wallet.save()
                
                # Credit to Seller
                seller_wallet.balance += total_cost
                seller_wallet.save()
                
                # Create Transaction record
                txn = Transaction.objects.create(
                    buyer=request.user,
                    seller=product.seller,
                    product=product,
                    amount=total_cost,
                    status='PAID'
                )
                
                # Create Notifications
                # 1. To Seller
                Notification.objects.create(
                    user=product.seller,
                    type='ITEM_SOLD',
                    message=f"Your item '{product.title}' has been sold for ${total_cost}!"
                )
                # 2. To Buyer
                Notification.objects.create(
                    user=request.user,
                    type='AUCTION_WON', # Reusing this type for direct purchase for now
                    message=f"You successfully purchased '{product.title}'!"
                )
                
                # Update Product Status
                product.status = 'SOLD'
                product.is_active = False
                product.save()
                
                return redirect('order_success', pk=txn.id)
            else:
                messages.error(request, "Insufficient funds in your wallet.")
    
    return render(request, 'market/checkout.html', {'product': product})


def user_profile(request, pk):
    from django.db.models import Avg
    user = get_object_or_404(User, pk=pk)
    
    avg_rating = user.received_reviews.aggregate(Avg('rating'))['rating__avg']
    avg_rating = round(avg_rating, 1) if avg_rating else "N/A"
    
    return render(request, 'market/profile.html', {'profile_user': user, 'avg_rating': avg_rating})

@login_required
def product_detail(request, pk):
    from django.db.models import Avg
    product = get_object_or_404(Product, pk=pk)
    
    # Seller Rating
    seller_avg = product.seller.received_reviews.aggregate(Avg('rating'))['rating__avg']
    seller_rating = round(seller_avg, 1) if seller_avg else "New"

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'bid':
            amount = float(request.POST.get('amount'))
            try:
                BidService.place_bid(product, request.user, amount)
                messages.success(request, "Bid placed successfully!")
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, "An error occurred.")
                
        elif action == 'buy_now':
            if not product.buy_now_price:
                messages.error(request, "This item does not have a Buy Now price.")
            else:
                # Create Transaction immediately
                # Create Transaction immediately
                # Ensure wallets
                if not hasattr(request.user, 'wallet'): from users.models import Wallet; Wallet.objects.create(user=request.user)
                if not hasattr(product.seller, 'wallet'): from users.models import Wallet; Wallet.objects.create(user=product.seller)

                if request.user.wallet.balance >= product.buy_now_price:
                    # Transfer
                    request.user.wallet.balance -= product.buy_now_price
                    request.user.wallet.save()
                    product.seller.wallet.balance += product.buy_now_price
                    product.seller.wallet.save()

                    Transaction.objects.create(
                        buyer=request.user,
                        seller=product.seller,
                        product=product,
                        amount=product.buy_now_price,
                        status='PAID'
                    )
                    product.status = 'SOLD'
                    product.is_active = False
                    product.save()
                    messages.success(request, f"You successfully purchased {product.title}!")
                    return redirect('home')
                else:
                    messages.error(request, "Insufficient funds.")
                    return redirect('product_detail', pk=pk)
                messages.success(request, f"You successfully purchased {product.title}!")
                return redirect('home')
        
        return redirect('product_detail', pk=pk)

    return render(request, 'product_detail.html', {'product': product, 'seller_rating': seller_rating})

@login_required
def dashboard(request):
    user = request.user
    # Stats
    active_products = Product.objects.filter(seller=user, is_active=True)
    sold_products = Product.objects.filter(seller=user, is_active=False) # Simplified for now, should check Transaction
    
    # Calculate Total Sales from Transactions
    total_sales = Transaction.objects.filter(seller=user, status='PAID').aggregate(total=models.Sum('amount'))['total'] or 0
    total_orders = Transaction.objects.filter(seller=user, status='PAID').count()
    
    # Recent Sales (Seller)
    recent_transactions = Transaction.objects.filter(seller=user).order_by('-transaction_date')[:5]

    # --- BUYER STATS ---
    purchases = Transaction.objects.filter(buyer=user).order_by('-transaction_date')
    total_spent = purchases.aggregate(total=models.Sum('amount'))['total'] or 0
    purchases_count = purchases.count()

    # --- REVIEWS ---
    written_reviews = Review.objects.filter(author=user).order_by('-created_at')

    context = {
        # Seller Context
        'active_count': active_products.count(),
        'sold_count': sold_products.count(),
        'total_sales': total_sales,
        'recent_transactions': recent_transactions,
        'active_products': active_products,
        
        # Buyer Context
        'total_spent': total_spent,
        'purchases_count': purchases_count,
        'recent_purchases': purchases[:10], # Show last 10
        'written_reviews': written_reviews,
    }
    return render(request, 'market/dashboard.html', context)

@login_required
def order_success(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, buyer=request.user)
    return render(request, 'market/order_success.html', {'transaction': txn})

@login_required
def deposit_funds(request):
    if request.method == 'POST':
        amount_raw = request.POST.get('amount')
        try:
            # Convertimos directamente a Decimal (usando el string del POST)
            amount = Decimal(amount_raw)
            
            if amount > 0:
                # Asegurar que el usuario tenga una billetera
                # (Mejor usar get_or_create para evitar errores)
                wallet, created = Wallet.objects.get_or_create(user=request.user)
                
                # Realizar la operación (Decimal + Decimal)
                wallet.balance += amount
                wallet.save()
                
                messages.success(request, f"Successfully deposited ${amount}!")
                return redirect('dashboard')
            else:
                messages.error(request, "Amount must be positive.")
        except (ValueError, InvalidOperation):
            messages.error(request, "Invalid amount format.")
            
    return render(request, 'market/deposit.html')

def help_center(request):
    return render(request, 'pages/help_center.html')

def terms(request):
    return render(request, 'pages/terms.html')

def privacy(request):
    return render(request, 'pages/privacy.html')

@login_required
def contact(request):
    from django.core.mail import send_mail
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        user_msg = f"Message from {name} <{email}>:\n\n{message}"
        
        try:
            send_mail(  
                subject=f"Nexus Contact: {name}",
                message=user_msg,
                from_email=None, # Uses DEFAULT_FROM_EMAIL
                recipient_list=['admin@nexus.com'], # Configure admin email
                fail_silently=False,
            )
            messages.success(request, f"Thanks {name}! Your message has been sent. We'll get back to you shortly.")
        except Exception as e:
            messages.error(request, "Failed to send message. Please try again later.")
            print(f"Email Error: {e}")
            
        return redirect('contact')
    return render(request, 'pages/contact.html')

@login_required
def leave_review(request, transaction_id):
    from transactions.models import Transaction, Review

    txn = get_object_or_404(Transaction, pk=transaction_id, buyer=request.user)
    
    # Validation: Only reviewed once
    if Review.objects.filter(transaction=txn).exists():
        messages.warning(request, "You have already reviewed this transaction.")
        return redirect('dashboard')

    if request.method == 'POST':
        rating_val = request.POST.get('rating')
        comment_val = request.POST.get('comment')
        
        if rating_val and comment_val:
            Review.objects.create(
                author=request.user,
                target_user=txn.seller,
                transaction=txn,
                rating=int(rating_val),
                comment=comment_val
            )
            messages.success(request, "Review submitted successfully!")
            return redirect('dashboard')
        else:
             messages.error(request, "Please provide both a rating and a comment.")

    return render(request, 'market/leave_review.html', {'transaction': txn})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.bio = request.POST.get('bio', user.bio)
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('user_profile', pk=user.id)
        
    return render(request, 'market/edit_profile.html')
