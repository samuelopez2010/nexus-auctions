import os
import requests
import zipfile
import pandas as pd
import io
import time
from django.core.management.base import BaseCommand
from core.models import Movie, Genre, Rating, CustomUser
from django.conf import settings

MOVIELENS_URL = 'https://files.grouplens.org/datasets/movielens/ml-latest-small.zip'
TMDB_API_KEY = os.environ.get('TMDB_API_KEY') # User must set this
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

class Command(BaseCommand):
    help = 'Ingest MovieLens data and TMDB metadata'

    def handle(self, *args, **options):
        # 1. Download & Unzip Data
        data_dir = settings.BASE_DIR / 'data'
        if not (data_dir / 'ml-latest-small').exists():
            self.stdout.write("Downloading MovieLens dataset...")
            r = requests.get(MOVIELENS_URL)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(data_dir)
            self.stdout.write("Downloaded and Extracted.")
        
        ml_dir = data_dir / 'ml-latest-small'
        
        # 2. Read CSVs
        links = pd.read_csv(ml_dir / 'links.csv')
        movies_df = pd.read_csv(ml_dir / 'movies.csv')
        
        # Merge to get tmdbId
        df = pd.merge(movies_df, links, on='movieId')
        
        # 3. Process Movies (Limit to top 50 for demo speed, or loop all)
        # Taking top 50 mostly populated movies to save API calls
        self.stdout.write("Processing Top 50 Movies...")
        
        count = 0
        for index, row in df.iterrows():
            if count >= 50: break 
            
            tmdb_id = row['tmdbId']
            if pd.isna(tmdb_id): continue
            
            tmdb_id = int(tmdb_id)
            
            # Check if exists
            # Check if exists and has valid data
            movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
            if movie and "Missing API Key" not in movie.overview:
                count += 1
                continue
            
            # Fetch TMDB Data
            if not TMDB_API_KEY:
                self.stdout.write(self.style.WARNING("TMDB_API_KEY not found. Skipping enrichment."))
                # Create basic
                movie = Movie.objects.create(
                    title=row['title'],
                    tmdb_id=tmdb_id,
                    overview="No overview available (Missing API Key).",
                    vote_average=5.0
                )
            else:
                try:
                    resp = requests.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}?api_key={TMDB_API_KEY}")
                    if resp.status_code != 200:
                        self.stdout.write(f"Failed to fetch TMDB ID {tmdb_id}")
                        continue
                    
                    data = resp.json()
                    
                    movie, _ = Movie.objects.update_or_create(
                        tmdb_id=tmdb_id,
                        defaults={
                            'title': data.get('title', row['title']),
                            'overview': data.get('overview', ''),
                            'release_date': data.get('release_date') or None,
                            'poster_path': data.get('poster_path'),
                            'backdrop_path': data.get('backdrop_path'),
                            'vote_average': data.get('vote_average', 0.0),
                            'popularity': data.get('popularity', 0.0),
                            'keywords': []
                        }
                    )
                    
                    # Genres
                    for g_data in data.get('genres', []):
                        genre, _ = Genre.objects.get_or_create(
                            tmdb_id=g_data['id'],
                            defaults={'name': g_data['name']}
                        )
                        movie.genres.add(genre)
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing {tmdb_id}: {e}"))
                    continue
            
            self.stdout.write(f"Created Movie: {movie.title}")
            count += 1
            time.sleep(0.1) # Respect API rate limits
            
        self.stdout.write(self.style.SUCCESS("Ingestion Complete."))
