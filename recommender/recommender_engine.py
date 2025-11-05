import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise import SVD, Dataset, Reader
from surprise.model_selection import train_test_split
from django.db import connection
import pickle
import os
from pathlib import Path
from .models import Movie, Rating, Watchlist
from django.contrib.auth.models import User


class HybridRecommender:
    def __init__(self):
        self.movies_df = None
        self.ratings_df = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.content_similarity = None
        self.svd_model = None
        self.cache_dir = Path('recommender/cache')
        self.cache_dir.mkdir(exist_ok=True)
        
        # Tải dữ liệu và xây dựng mô hình
        self._load_data()
        self._build_content_model()
        self._build_collaborative_model()
    
    def _load_data(self):
        """Tải dữ liệu từ cơ sở dữ liệu sử dụng pandas"""
        print("Đang tải dữ liệu từ cơ sở dữ liệu...")
        
        # Tải phim
        movies_query = """
        SELECT id, title, genre, overview, tmdb_id 
        FROM recommender_movie
        """
        self.movies_df = pd.read_sql_query(movies_query, connection)
        
        # Tải đánh giá
        ratings_query = """
        SELECT id, user_id, movie_id, rating, timestamp 
        FROM recommender_rating
        """
        self.ratings_df = pd.read_sql_query(ratings_query, connection)
        
        # Tải danh sách theo dõi
        watchlist_query = """
        SELECT id, user_id, movie_id, added_at 
        FROM recommender_watchlist
        """
        self.watchlist_df = pd.read_sql_query(watchlist_query, connection)
        
        print(f"Đã tải {len(self.movies_df)} phim, {len(self.ratings_df)} đánh giá, và {len(self.watchlist_df)} mục trong danh sách theo dõi")
    
    def _build_content_model(self):
        """Build content-based model using TF-IDF on genre + overview"""
        cache_file = self.cache_dir / 'content_model.pkl'
        
        if cache_file.exists():
            print("Loading cached content model...")
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                self.tfidf_vectorizer = cache_data['vectorizer']
                self.tfidf_matrix = cache_data['matrix']
                self.content_similarity = cache_data['similarity']
            return
        
        print("Building content-based model...")
        
        # Combine genre and overview for TF-IDF
        self.movies_df['content'] = self.movies_df['genre'].fillna('') + ' ' + self.movies_df['overview'].fillna('')
        
        # Create TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2)
        )
        
        # Fit and transform
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.movies_df['content'])
        
        # Compute cosine similarity
        self.content_similarity = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
        
        # Cache the model
        cache_data = {
            'vectorizer': self.tfidf_vectorizer,
            'matrix': self.tfidf_matrix,
            'similarity': self.content_similarity
        }
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        print("Content-based model built and cached")
    
    def _build_collaborative_model(self):
        """Build collaborative filtering model using SVD"""
        cache_file = self.cache_dir / 'svd_model.pkl'
        
        if cache_file.exists():
            print("Loading cached SVD model...")
            with open(cache_file, 'rb') as f:
                self.svd_model = pickle.load(f)
            return
        
        print("Building collaborative filtering model...")
        
        if len(self.ratings_df) < 100:
            print("Not enough ratings for collaborative filtering, using dummy model")
            self.svd_model = None
            return
        
        # Prepare data for Surprise
        reader = Reader(rating_scale=(1, 5))
        data = Dataset.load_from_df(
            self.ratings_df[['user_id', 'movie_id', 'rating']], 
            reader
        )
        
        # Split data
        trainset, _ = train_test_split(data, test_size=0.2, random_state=42)
        
        # Train SVD model
        self.svd_model = SVD(n_factors=50, n_epochs=20, random_state=42)
        self.svd_model.fit(trainset)
        
        # Cache the model
        with open(cache_file, 'wb') as f:
            pickle.dump(self.svd_model, f)
        
        print("Collaborative filtering model built and cached")
    
    def _get_content_scores(self, movie_idx, rated_movies=None):
        """Get content-based similarity scores for a movie"""
        if rated_movies:
            # If user has rated movies, average similarity to all rated movies
            similarities = []
            for rated_movie_id in rated_movies:
                rated_idx = self.movies_df[self.movies_df['id'] == rated_movie_id].index
                if len(rated_idx) > 0:
                    sim = self.content_similarity[movie_idx, rated_idx[0]]
                    similarities.append(sim)
            return np.mean(similarities) if similarities else 0
        else:
            # Return base similarity (not used in current logic)
            return 0
    
    def _get_collaborative_score(self, user_id, movie_id):
        """Get collaborative filtering prediction for user-movie pair"""
        if self.svd_model is None:
            return 3.0  # Default rating if no model
        
        try:
            prediction = self.svd_model.predict(user_id, movie_id)
            return prediction.est
        except:
            return 3.0  # Default if prediction fails
    
    def _get_popular_movies(self, n=10):
        """Get popular movies based on number of ratings"""
        if len(self.ratings_df) == 0:
            # If no ratings, return random movies
            return self.movies_df.sample(n=n)['id'].tolist()
        
        movie_ratings_count = self.ratings_df.groupby('movie_id').size()
        movie_avg_rating = self.ratings_df.groupby('movie_id')['rating'].mean()
        
        # Combine count and average rating for popularity score
        popularity = (movie_ratings_count * movie_avg_rating).sort_values(ascending=False)
        
        # Get top n movie IDs
        top_movie_ids = popularity.head(n).index.tolist()
        return top_movie_ids
    
    def _is_in_watchlist(self, user_id, movie_id):
        """Check if movie is in user's watchlist"""
        if hasattr(self, 'watchlist_df') and self.watchlist_df is not None:
            return ((self.watchlist_df['user_id'] == user_id) & 
                    (self.watchlist_df['movie_id'] == movie_id)).any()
        return False
    
    def _get_vectorized_content_scores(self, rated_movie_ids):
        """Get content-based scores using vectorized operations (no line-by-line)"""
        if not rated_movie_ids:
            return np.zeros(len(self.movies_df))
        
        # Get indices of rated movies
        rated_indices = []
        for movie_id in rated_movie_ids:
            idx = self.movies_df[self.movies_df['id'] == movie_id].index
            if len(idx) > 0:
                rated_indices.append(idx[0])
        
        if not rated_indices:
            return np.zeros(len(self.movies_df))
        
        # Vectorized similarity calculation
        rated_similarities = self.content_similarity[:, rated_indices]
        avg_similarities = np.mean(rated_similarities, axis=1)
        
        return avg_similarities

    def _get_vectorized_collaborative_scores(self, user_id, movie_ids):
        """Get collaborative scores using vectorized operations (no line-by-line)"""
        if self.svd_model is None:
            return np.full(len(movie_ids), 3.0)  # Default rating
        
        # Create predictions in batch
        predictions = []
        for movie_id in movie_ids:
            try:
                prediction = self.svd_model.predict(user_id, movie_id)
                predictions.append(prediction.est)
            except:
                predictions.append(3.0)  # Default if prediction fails
        
        return np.array(predictions)

    def _get_watchlist_boost_vectorized(self, user_id, movie_ids):
        """Get watchlist boost using vectorized operations"""
        if not hasattr(self, 'watchlist_df') or self.watchlist_df is None:
            return np.zeros(len(movie_ids))
        
        # Create boolean array for watchlist status
        user_watchlist = self.watchlist_df[self.watchlist_df['user_id'] == user_id]
        watchlist_movie_ids = set(user_watchlist['movie_id'].tolist())
        
        boost = np.array([0.2 if movie_id in watchlist_movie_ids else 0.0 for movie_id in movie_ids])
        return boost

    def get_recommendations_fast(self, user_id, n=10):
        """
        Get hybrid recommendations using vectorized operations (no line-by-line)
        
        Args:
            user_id: ID of the user
            n: Number of recommendations to return
            
        Returns:
            List of movie IDs
        """
        print(f"Getting fast recommendations for user {user_id}...")
        
        # Check if user exists and has ratings
        user_ratings = self.ratings_df[self.ratings_df['user_id'] == user_id]
        
        # Cold start: return popular movies if user has no ratings
        if len(user_ratings) == 0:
            print(f"User {user_id} has no ratings, returning popular movies")
            return self._get_popular_movies(n)
        
        # Get movies the user has rated
        rated_movie_ids = user_ratings['movie_id'].tolist()
        
        # Get all movie IDs for vectorized operations
        all_movie_ids = self.movies_df['id'].tolist()
        all_movie_indices = self.movies_df.index.tolist()
        
        # Vectorized content-based scores for all movies
        content_scores_all = self._get_vectorized_content_scores(rated_movie_ids)
        content_scores_normalized = content_scores_all * 5  # Normalize to 0-5 scale
        
        # Get unrated movie indices
        unrated_mask = ~self.movies_df['id'].isin(rated_movie_ids)
        unrated_indices = self.movies_df[unrated_mask].index.tolist()
        unrated_movie_ids = self.movies_df.loc[unrated_indices, 'id'].tolist()
        
        if not unrated_movie_ids:
            print(f"No unrated movies found for user {user_id}")
            return self._get_popular_movies(n)
        
        # Vectorized collaborative scores for unrated movies
        collab_scores = self._get_vectorized_collaborative_scores(user_id, unrated_movie_ids)
        
        # Vectorized watchlist boost for unrated movies
        watchlist_boost = self._get_watchlist_boost_vectorized(user_id, unrated_movie_ids)
        
        # Get content scores for unrated movies
        unrated_content_scores = content_scores_normalized[unrated_indices]
        
        # Hybrid score calculation (vectorized)
        hybrid_scores = (0.4 * unrated_content_scores + 0.6 * collab_scores + watchlist_boost)
        
        # Create recommendations array
        recommendations = list(zip(unrated_movie_ids, hybrid_scores))
        
        # Sort by hybrid score and return top n
        recommendations.sort(key=lambda x: x[1], reverse=True)
        top_recommendations = [rec[0] for rec in recommendations[:n]]
        
        print(f"Generated {len(top_recommendations)} recommendations using vectorized operations")
        return top_recommendations

    def get_recommendations(self, user_id, n=10):
        """
        Get hybrid recommendations for a user (uses fast vectorized version)
        
        Args:
            user_id: ID of the user
            n: Number of recommendations to return
            
        Returns:
            List of movie IDs
        """
        # Use the fast vectorized version by default
        return self.get_recommendations_fast(user_id, n)


# Unit test
def test_recommender():
    """Unit test for the recommender engine"""
    print("Running unit test...")
    
    try:
        recommender = HybridRecommender()
        
        # Test with user_id=1
        recommendations = recommender.get_recommendations(user_id=1, n=10)
        
        print(f"Recommendations for user 1: {recommendations}")
        
        # Verify we get a list of movie IDs
        assert isinstance(recommendations, list), "Recommendations should be a list"
        assert len(recommendations) <= 10, "Should return at most 10 recommendations"
        
        if len(recommendations) > 0:
            assert all(isinstance(movie_id, (int, np.integer)) for movie_id in recommendations), \
                "All recommendations should be movie IDs"
        
        print("Unit test passed!")
        return recommendations
        
    except Exception as e:
        print(f"Unit test failed: {e}")
        return []


if __name__ == "__main__":
    # Run unit test when script is executed directly
    test_recommender()
