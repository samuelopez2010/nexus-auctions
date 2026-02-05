from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('welcome/setup/', onboarding_view, name='onboarding'),
    path('movie/<int:pk>/', MovieDetailView.as_view(), name='movie_detail'),
    path('movie/<int:movie_id>/rate/', rate_movie, name='rate_movie'),
    path('movie/<int:movie_id>/watchlist/', toggle_watchlist, name='toggle_watchlist'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]
