from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Count
from .models import Movie, Rating, UserRecommendation, CustomUser, Watchlist, Genre
from .forms import CustomUserCreationForm
from .tasks import calculate_recommendations
import json
import random

class RegisterView(CreateView):
    template_name = 'registration/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('onboarding')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('onboarding')

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    
    def get_success_url(self):
        # Redirect to onboarding if no ratings? Or just Home
        if not Rating.objects.filter(user=self.request.user).exists():
             return reverse_lazy('onboarding')
        return reverse_lazy('home')

def onboarding_view(request):
    if request.method == 'POST':
        movie_ids = request.POST.getlist('movies')
        # Expecting at least 3
        if len(movie_ids) < 3:
            return render(request, 'onboarding.html', {
                'movies': Movie.objects.order_by('-popularity')[:30],
                'error': 'Please select at least 3 movies.'
            })
        
        # Create ratings
        for mid in movie_ids:
            Rating.objects.update_or_create(
                user=request.user, movie_id=mid,
                defaults={'score': 5}
            )
        
        # Trigger Celery Task
        calculate_recommendations.delay(request.user.id)
        
        return redirect('home')
        
    # GET: Show grid of popular movies
    movies = Movie.objects.order_by('-popularity')[:30]
    return render(request, 'onboarding.html', {'movies': movies})

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 1. Recommendations
        recs = []
        try:
            user_recs = UserRecommendation.objects.get(user=user)
            rec_ids = user_recs.recommendations
            # Preserve order
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(rec_ids)])
            recs = Movie.objects.filter(id__in=rec_ids) # .order_by(preserved) if needed, but filter is enough for demo
        except UserRecommendation.DoesNotExist:
            recs = []

        context['recommendations'] = recs
        
        # 2. Trending
        context['trending'] = Movie.objects.order_by('-popularity')[:12]
        
        # 3. Because you watched... (Find last liked)
        last_liked = Rating.objects.filter(user=user, score__gte=4).order_by('-timestamp').first()
        if last_liked:
            context['because_movie'] = last_liked.movie
            # Simple retrieval here or use ContentEngine logic again
            # For simplicity in view, just random or same genre
            context['similar_movies'] = Movie.objects.filter(genres__in=last_liked.movie.genres.all()).distinct().exclude(id=last_liked.movie.id)[:10]
            
        return context

from django.db.models import Case, When

class MovieDetailView(DetailView):
    model = Movie
    template_name = 'movie_detail.html'
    context_object_name = 'movie'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movie = self.object
        
        # Radar Chart Data
        # Axis: Pace, Visuals, Plot, Acting, Sound, Complexity
        # Simulate based on genres
        genres = [g.name for g in movie.genres.all()]
        data = {
            'Pace': 8 if 'Action' in genres or 'Adventure' in genres else 4,
            'Visuals': 9 if 'Sci-Fi' in genres or 'Fantasy' in genres else 5,
            'Plot': 8 if 'Mystery' in genres or 'Thriller' in genres else 5,
            'Acting': 8 if 'Drama' in genres else 5,
            'Sound': 7, # Generic
            'Complexity': 9 if 'Science Fiction' in genres else 4
        }
        # Add random variance
        for k in data:
            data[k] = min(10, max(1, data[k] + random.randint(-1, 2)))
            
        context['radar_data'] = json.dumps(data)
        
        # Similar movies (using shared genres for now, replacing with real Sim Matrix if available)
        context['similar_movies'] = Movie.objects.filter(genres__in=movie.genres.all()).distinct().exclude(id=movie.id).order_by('?')[:6]
        
        # User Rating if exists
        context['user_rating'] = 0
        if self.request.user.is_authenticated:
            r = Rating.objects.filter(user=self.request.user, movie=movie).first()
            if r: context['user_rating'] = r.score
            context['in_watchlist'] = Watchlist.objects.filter(user=self.request.user, movie=movie).exists()
            
        return context

def rate_movie(request, movie_id):
    if request.method == 'POST' and request.user.is_authenticated:
        score = int(request.POST.get('score'))
        Rating.objects.update_or_create(
            user=request.user, movie_id=movie_id,
            defaults={'score': score}
        )
        
        # Check re-training trigger
        count = Rating.objects.filter(user=request.user).count()
        if count % 10 == 0:
            calculate_recommendations.delay(request.user.id)
            
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def toggle_watchlist(request, movie_id):
    if request.method == 'POST' and request.user.is_authenticated:
        w, created = Watchlist.objects.get_or_create(user=request.user, movie_id=movie_id)
        if not created:
            w.delete()
            return JsonResponse({'status': 'removed'})
        return JsonResponse({'status': 'added'})
    return JsonResponse({'status': 'error'}, status=400)

class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['watchlist'] = Movie.objects.filter(watchlist__user=user)
        context['ratings'] = Rating.objects.filter(user=user).select_related('movie')
        
        # Stats for Chart.js
        # Count genres in liked movies
        liked_movies = Rating.objects.filter(user=user, score__gte=4).values_list('movie', flat=True)
        genres = Genre.objects.filter(movie__in=liked_movies).values('name').annotate(count=Count('name')).order_by('-count')
        
        labels = [g['name'] for g in genres]
        data = [g['count'] for g in genres]
        
        context['genre_stats'] = json.dumps({'labels': labels, 'data': data})
        
        return context
