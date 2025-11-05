#!/usr/bin/env python3
import os
import sys
import csv
import pandas as pd
from django.db import transaction
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recsys.settings')

import django
django.setup()

from recommender.models import Movie, Rating, Watchlist
from django.contrib.auth.models import User

# Configuration for fast testing
SAMPLE_SIZE = 1000  # Only import first 1000 rows for testing
BATCH_SIZE = 100    # Smaller batch size for testing

def clear_existing_data():
    """Clear existing data to avoid conflicts"""
    print("Clearing existing data...")
    
    # Clear data in correct order to handle foreign key constraints
    Watchlist.objects.all().delete()
    Rating.objects.all().delete()
    Movie.objects.all().delete()
    
    # Delete users created by previous imports (non-staff, non-superuser)
    User.objects.filter(username__startswith='user_', is_staff=False, is_superuser=False).delete()
    User.objects.filter(username='demo_user', is_staff=False, is_superuser=False).delete()
    
    print("Existing data cleared successfully")

def import_movies():
    """Import movies from movies.csv - limited sample for testing"""
    print(f"Importing first {SAMPLE_SIZE} movies from movies.csv...")
    movies_file = "data/ml-20m/movies.csv"
    
    movies_to_create = []
    count = 0
    
    with open(movies_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if count >= SAMPLE_SIZE:
                break
                
            # Extract year from title (format: "Title (Year)")
            title = row['title']
            release_year = None
            if '(' in title and ')' in title:
                try:
                    year_str = title.split('(')[-1].split(')')[0]
                    if year_str.isdigit():
                        release_year = int(year_str)
                except:
                    pass
            
            # Use the first genre as the main genre
            genres = row['genres'].split('|')
            main_genre = genres[0] if genres else 'Unknown'
            
            movie = Movie(
                title=title,
                genre=main_genre,
                director='Unknown',
                release_year=release_year or 0,
                overview='No overview available',
                poster_url=None,
                tmdb_id=int(row['movieId'])
            )
            movies_to_create.append(movie)
            count += 1
    
    # Bulk create in batches
    for i in range(0, len(movies_to_create), BATCH_SIZE):
        batch = movies_to_create[i:i + BATCH_SIZE]
        Movie.objects.bulk_create(batch, ignore_conflicts=True)
        print(f"Created {min(i + BATCH_SIZE, len(movies_to_create))} movies...")
    
    print(f"Successfully imported {len(movies_to_create)} movies")

def import_ratings():
    """Import ratings from ratings.csv - limited sample for testing"""
    print(f"Importing first {SAMPLE_SIZE} ratings from ratings.csv...")
    ratings_file = "data/ml-20m/ratings.csv"
    
    # Get all movies for mapping
    movies_dict = {movie.tmdb_id: movie for movie in Movie.objects.all()}
    
    ratings_to_create = []
    count = 0
    
    with open(ratings_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if count >= SAMPLE_SIZE:
                break
                
            movie_id = int(row['movieId'])
            user_id = int(row['userId'])
            
            # Get or create user
            user, created = User.objects.get_or_create(
                username=f'user_{user_id}',
                defaults={'email': f'user_{user_id}@example.com', 'password': 'defaultpass123'}
            )
            
            # Get movie
            movie = movies_dict.get(movie_id)
            if movie:
                rating = Rating(
                    user=user,
                    movie=movie,
                    rating=float(row['rating']),
                    timestamp=datetime.fromtimestamp(int(row['timestamp']))
                )
                ratings_to_create.append(rating)
                count += 1
    
    # Bulk create in batches
    for i in range(0, len(ratings_to_create), BATCH_SIZE):
        batch = ratings_to_create[i:i + BATCH_SIZE]
        Rating.objects.bulk_create(batch, ignore_conflicts=True)
        print(f"Created {min(i + BATCH_SIZE, len(ratings_to_create))} ratings...")
    
    print(f"Successfully imported {len(ratings_to_create)} ratings")

def create_test_user():
    """Create a test user for demonstration"""
    test_user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={
            'email': 'demo@example.com',
            'password': 'demopass123'
        }
    )
    if created:
        test_user.set_password('demopass123')
        test_user.save()
        print("Created demo user: demo_user / demopass123")

@transaction.atomic
def main():
    """Main function to import limited CSV data for testing"""
    print("Starting FAST CSV data import (limited sample)...")
    
    print("Step 0: Clearing existing data...")
    clear_existing_data()
    
    print("Step 1: Importing movies...")
    import_movies()
    
    print("Step 2: Importing ratings...")
    import_ratings()
    
    print("Step 3: Creating test user...")
    create_test_user()
    
    print("\nFAST CSV data import completed successfully!")
    print(f"Total movies in database: {Movie.objects.count()}")
    print(f"Total ratings in database: {Rating.objects.count()}")
    print(f"Total users in database: {User.objects.count()}")

if __name__ == '__main__':
    main()
