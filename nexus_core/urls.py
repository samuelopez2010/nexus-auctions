from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, AddressViewSet
from market.views import CategoryViewSet, ProductViewSet
from transactions.views import TransactionViewSet, NotificationViewSet
from market.frontend_views import (
    home, product_detail, create_product, user_profile, dashboard, 
    checkout, catalog, notifications_view, deposit_funds, order_success, gift_cards,
    help_center, terms, privacy, contact, leave_review, edit_profile
)
from market.auth_views import login_view, logout_view, signup_view
from market.payment_views import create_checkout_session, stripe_webhook, payment_success
from transactions.views import download_invoice

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'notifications', NotificationViewSet, basename='notification')

# ... existing router setup ...

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('catalog/', catalog, name='catalog'),
    path('notifications/', notifications_view, name='notifications'), # Notifications
    path('dashboard/', dashboard, name='dashboard'),
    path('wallet/deposit/', deposit_funds, name='deposit_funds'),
    path('gift-cards/', gift_cards, name='gift_cards'),
    path('order-confirmed/<int:pk>/', order_success, name='order_success'),
    path('invoice/<int:transaction_id>/', download_invoice, name='download_invoice'), # Invoice Download
    path('create/', create_product, name='create_product'),
    path('review/<int:transaction_id>/', leave_review, name='leave_review'),
    path('product/<int:pk>/', product_detail, name='product_detail'),
    path('checkout/<int:pk>/', checkout, name='checkout'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/<int:pk>/', user_profile, name='user_profile'),
    
    # Payments
    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),
    path('wallet/success/', payment_success, name='payment_success'),
    
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    
    # footer pages
    path('help/', help_center, name='help_center'),
    path('terms/', terms, name='terms'),
    path('privacy/', privacy, name='privacy'),
    path('contact/', contact, name='contact'),

    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
