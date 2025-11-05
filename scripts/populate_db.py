import os
import sys
import csv
import time
import requests
from django.db import transaction

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recsys.settings')

import django
django.setup()

from recommender.models import Movie, Rating
from django.contrib.auth.models import User

# Configuration
TMDB_API_KEY = ""  # Skip TMDb API for now
TMDB_BASE_URL = "https://api.themoviedb.org/3"
SLEEP_TIME = 0.1  # Rate limiting sleep time in seconds
MAX_MOVIES = 100  # Only process first 100 movies for testing

def get_tmdb_movie_details(tmdb_id):
    """Get movie details from TMDb API"""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        overview = data.get('overview', '')
        poster_path = data.get('poster_path', '')
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        
        return overview, poster_url
    except requests.exceptions.RequestException as e:
        print(f"Error fetching TMDb data for ID {tmdb_id}: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error for ID {tmdb_id}: {e}")
        return None, None

def populate_movies():
    """Populate Movie objects with sample data (no TMDb API)"""
    # Dữ liệu phim mẫu để kiểm thử với hình ảnh thực tế
    sample_movies = [
        {
            'title': 'The Shawshank Redemption',
            'genre': 'Drama',
            'release_year': 1994,
            'overview': 'Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg',
            'director': 'Frank Darabont'
        },
        {
            'title': 'The Godfather',
            'genre': 'Crime|Drama',
            'release_year': 1972,
            'overview': 'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg',
            'director': 'Francis Ford Coppola'
        },
        {
            'title': 'The Dark Knight',
            'genre': 'Action|Crime|Drama',
            'release_year': 2008,
            'overview': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg',
            'director': 'Christopher Nolan'
        },
        {
            'title': 'Pulp Fiction',
            'genre': 'Crime|Drama',
            'release_year': 1994,
            'overview': 'The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg',
            'director': 'Quentin Tarantino'
        },
        {
            'title': 'Forrest Gump',
            'genre': 'Drama|Romance',
            'release_year': 1994,
            'overview': 'The presidencies of Kennedy and Johnson, the Vietnam War, the Watergate scandal and other historical events unfold from the perspective of an Alabama man with an IQ of 75.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg',
            'director': 'Robert Zemeckis'
        },
        {
            'title': 'Inception',
            'genre': 'Action|Adventure|Sci-Fi',
            'release_year': 2010,
            'overview': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/9gk7adHYeDvHkCSEqAvQNLV5Uge.jpg',
            'director': 'Christopher Nolan'
        },
        {
            'title': 'The Matrix',
            'genre': 'Action|Sci-Fi',
            'release_year': 1999,
            'overview': 'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg',
            'director': 'Lana Wachowski, Lilly Wachowski'
        },
        {
            'title': 'Goodfellas',
            'genre': 'Biography|Crime|Drama',
            'release_year': 1990,
            'overview': 'The story of Henry Hill and his life in the mob, covering his relationship with his wife Karen Hill and his mob partners Jimmy Conway and Tommy DeVito.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/aKuFiU82s5ISJpGZp7YkIr3kCUd.jpg',
            'director': 'Martin Scorsese'
        },
        {
            'title': 'The Silence of the Lambs',
            'genre': 'Crime|Drama|Thriller',
            'release_year': 1991,
            'overview': 'A young F.B.I. cadet must receive the help of an incarcerated and manipulative cannibal killer to help catch another serial killer.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/uS9m8OBk1A8eM9I042bx8XXpqAq.jpg',
            'director': 'Jonathan Demme'
        },
        {
            'title': 'The Lord of the Rings: The Fellowship of the Ring',
            'genre': 'Adventure|Drama|Fantasy',
            'release_year': 2001,
            'overview': 'A meek Hobbit from the Shire and eight companions set out on a journey to destroy the powerful One Ring and save Middle-earth from the Dark Lord Sauron.',
            'poster_url': 'https://image.tmdb.org/t/p/w500/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg',
            'director': 'Peter Jackson'
        }
    ]
    
    movies_to_create = []
    for i, movie_data in enumerate(sample_movies):
        movie = Movie(
            title=movie_data['title'],
            genre=movie_data['genre'],
            director=movie_data['director'],
            release_year=movie_data['release_year'],
            overview=movie_data['overview'],
            poster_url=movie_data['poster_url'],
            tmdb_id=1000 + i  # Simple fake TMDb IDs
        )
        movies_to_create.append(movie)
    
    # Bulk create movies
    try:
        Movie.objects.bulk_create(movies_to_create, ignore_conflicts=True)
        print(f"Successfully created {len(movies_to_create)} sample movies")
    except Exception as e:
        print(f"Error bulk creating movies: {e}")

def populate_ratings():
    """Populate Rating objects with sample data"""
    # Get all movies from the database
    movies = list(Movie.objects.all())
    if not movies:
        print("No movies found in database. Please run populate_movies first.")
        return
    
    # Get or create a test user
    test_user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com', 'password': 'testpass123'}
    )
    if created:
        print("Created test user")
    
    # Create sample ratings for the test user
    ratings_to_create = []
    for movie in movies:
        # Assign random ratings between 3.0 and 5.0 for testing
        import random
        rating_value = round(random.uniform(3.0, 5.0), 1)
        
        rating = Rating(
            user=test_user,
            movie=movie,
            rating=rating_value
        )
        ratings_to_create.append(rating)
    
    # Bulk create ratings
    try:
        Rating.objects.bulk_create(ratings_to_create, ignore_conflicts=True)
        print(f"Successfully created {len(ratings_to_create)} sample ratings")
    except Exception as e:
        print(f"Error bulk creating ratings: {e}")

@transaction.atomic
def main():
    """Main function to populate database"""
    print("Starting database population...")
    
    print("Step 1: Populating movies...")
    populate_movies()
    
    print("Step 2: Populating ratings...")
    populate_ratings()
    
    print("Database population completed!")

if __name__ == '__main__':
    main()
