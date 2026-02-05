import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from .models import Movie, Rating

class ContentEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self.movie_ids = []

    def fit(self):
        """
        Builds the TF-IDF matrix from all movies in the database.
        Combines 'overview' + 'genres' + 'keywords' into a single string.
        """
        movies = Movie.objects.all()
        if not movies.exists():
            return
        
        self.movie_ids = [m.id for m in movies]
        
        # Prepare text data
        corpus = []
        for m in movies:
            genre_names = " ".join([g.name for g in m.genres.all()])
            keywords = " ".join(m.keywords) if m.keywords else ""
            # Upweight genres/keywords by repeating them? Or just concat.
            text = f"{genre_names} {keywords} {m.overview}"
            corpus.append(text)
            
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def predict(self, liked_movie_ids, top_n=10):
        """
        Returns top_n recommended movie IDs based on similarity to liked movies.
        """
        if self.tfidf_matrix is None:
            self.fit()
            if self.tfidf_matrix is None:
                return []

        # Map liked_movie_ids to indices in self.movie_ids
        liked_indices = [
            i for i, mid in enumerate(self.movie_ids) 
            if mid in liked_movie_ids
        ]
        
        if not liked_indices:
            return []

        # Create user profile vector: Mean of liked movies' vectors
        user_vector = self.tfidf_matrix[liked_indices].mean(axis=0)
        
        # Calculate cosine similarity between user vector and all movies
        # cosine_similarity returns shape (1, n_samples)
        sim_scores = cosine_similarity(user_vector, self.tfidf_matrix).flatten()
        
        # Sort indices by score (descending)
        sorted_indices = sim_scores.argsort()[::-1]
        
        recommendations = []
        for idx in sorted_indices:
            movie_id = self.movie_ids[idx]
            if movie_id not in liked_movie_ids: # Don't recommend what they already liked/watched
                recommendations.append(movie_id)
                if len(recommendations) >= top_n:
                    break
                    
        return recommendations

class CollaborativeEngine:
    def __init__(self):
        self.model = TruncatedSVD(n_components=20, random_state=42)
        self.user_item_matrix = None
        self.user_ids = []
        self.item_ids = []

    def fit(self):
        """
        Builds the User-Item matrix from Ratings.
        """
        ratings = Rating.objects.all().values('user_id', 'movie_id', 'score')
        df = pd.DataFrame(ratings)
        
        if df.empty:
            return

        # Pivot table: Rows=Users, Cols=Movies, Values=Score
        # Fill NaN with 0 (unseen)
        self.user_item_matrix = df.pivot(index='user_id', columns='movie_id', values='score').fillna(0)
        self.user_ids = self.user_item_matrix.index.tolist()
        self.item_ids = self.user_item_matrix.columns.tolist() # These are movie_ids

        # Train SVD
        n_features = self.user_item_matrix.shape[1]
        # n_components must be strictly less than n_features for some solvers, but sklearn says <=. 
        # However, to avoid trivial/error cases with tiny data:
        n_components = min(20, n_features - 1)
        
        if n_components < 1:
            # Fallback for extremely sparse data (not enough to reduce)
            # Use original matrix as "reconstructed"
            self.matrix_reduced = self.user_item_matrix.values
            self.matrix_reconstructed = self.user_item_matrix.values
        else:
            self.model = TruncatedSVD(n_components=n_components, random_state=42)
            self.matrix_reduced = self.model.fit_transform(self.user_item_matrix.values)
            self.matrix_reconstructed = self.model.inverse_transform(self.matrix_reduced)

    def predict(self, user_id, top_n=10):
        if self.user_item_matrix is None:
            self.fit()
            if self.user_item_matrix is None:
                return []
        
        if user_id not in self.user_ids:
            return [] # New user, cold start functionality should handle this, or return empty
        
        user_idx = self.user_ids.index(user_id)
        
        # Get predicted ratings for this user (row in reconstructed matrix)
        predicted_ratings = self.matrix_reconstructed[user_idx]
        
        # Filter already rated movies
        # Get actual ratings from the pivot table (0 means unrated)
        actual_ratings = self.user_item_matrix.iloc[user_idx]
        
        # Create list of (movie_id, predicted_score) where actual_rating is 0
        candidates = []
        for idx, score in enumerate(predicted_ratings):
            if actual_ratings.iloc[idx] == 0:
                movie_id = self.item_ids[idx]
                candidates.append((movie_id, score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return [c[0] for c in candidates[:top_n]]

# Unified Interface
class RecommenderSystem:
    def __init__(self):
        self.content_engine = ContentEngine()
        self.collab_engine = CollaborativeEngine()
    
    def train(self):
        self.content_engine.fit()
        self.collab_engine.fit()
    
    def get_recommendations(self, user_id, top_n=20):
        # Fetch user's liked movies for content-based
        # Assume 'liked' means rating >= 4
        liked_movies = Rating.objects.filter(user_id=user_id, score__gte=4).values_list('movie_id', flat=True)
        
        content_recs = self.content_engine.predict(list(liked_movies), top_n=top_n)
        collab_recs = self.collab_engine.predict(user_id, top_n=top_n)
        
        # Hybrid Strategy: Interleave
        # C = Content, K = Collab -> C, K, C, K
        hybrid_recs = []
        c_idx, k_idx = 0, 0
        seen = set()
        
        while len(hybrid_recs) < top_n:
            if c_idx < len(content_recs):
                m = content_recs[c_idx]
                if m not in seen:
                    hybrid_recs.append(m)
                    seen.add(m)
                c_idx += 1
            
            if len(hybrid_recs) >= top_n: break
            
            if k_idx < len(collab_recs):
                m = collab_recs[k_idx]
                if m not in seen:
                    hybrid_recs.append(m)
                    seen.add(m)
                k_idx += 1
                
            if c_idx >= len(content_recs) and k_idx >= len(collab_recs):
                break
                
        return hybrid_recs
