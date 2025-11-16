#!/usr/bin/env python3
import os
import sys
import csv
import pandas as pd
from django.db import transaction, connection
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movie_recsys.settings')

import django
django.setup()

from recommender.models import Movie, Rating, Watchlist
from django.contrib.auth.models import User

def import_movies():
    """Import movies from movies.csv"""
    print("Importing movies from movies.csv...")
    movies_file = "data/ml-20m/movies.csv"
    
    movies_to_create = []
    with open(movies_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
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
                director='Unknown',  # CSV doesn't have director info
                release_year=release_year or 0,
                overview='No overview available',
                poster_url=None,
                tmdb_id=int(row['movieId'])  # Using movieId as tmdb_id for now
            )
            movies_to_create.append(movie)
    
    # Bulk create in batches to avoid memory issues
    batch_size = 1000
    for i in range(0, len(movies_to_create), batch_size):
        batch = movies_to_create[i:i + batch_size]
        Movie.objects.bulk_create(batch, ignore_conflicts=True)
        print(f"Created {min(i + batch_size, len(movies_to_create))} movies...")
    
    print(f"Successfully imported {len(movies_to_create)} movies")

def import_ratings():
    """Import ratings from ratings.csv"""
    print("Importing ratings from ratings.csv...")
    ratings_file = "data/ml-20m/ratings.csv"
    
    # Get all movies for mapping
    movies_dict = {movie.tmdb_id: movie for movie in Movie.objects.all()}
    
    ratings_to_create = []
    with open(ratings_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
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
    
    # Bulk create in batches
    batch_size = 1000
    for i in range(0, len(ratings_to_create), batch_size):
        batch = ratings_to_create[i:i + batch_size]
        Rating.objects.bulk_create(batch, ignore_conflicts=True)
        print(f"Created {min(i + batch_size, len(ratings_to_create))} ratings...")
    
    print(f"Successfully imported {len(ratings_to_create)} ratings")

def import_links():
    """Import links data and update movies with proper tmdb_id"""
    print("Importing links data...")
    links_file = "data/ml-20m/links.csv"
    
    links_data = {}
    with open(links_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            movie_id = int(row['movieId'])
            tmdb_id = int(row['tmdbId']) if row['tmdbId'] else None
            links_data[movie_id] = tmdb_id
    
    # Update movies with proper tmdb_id from links, handling unique constraints
    updated_count = 0
    for movie in Movie.objects.all():
        if movie.tmdb_id in links_data and links_data[movie.tmdb_id]:
            new_tmdb_id = links_data[movie.tmdb_id]
            
            # Check if this tmdb_id is already used by another movie
            existing_movie = Movie.objects.filter(tmdb_id=new_tmdb_id).exclude(pk=movie.pk).first()
            if existing_movie:
                print(f"Warning: TMDb ID {new_tmdb_id} already used by movie '{existing_movie.title}'. Skipping update for '{movie.title}'.")
                continue
            
            # Update the movie
            movie.tmdb_id = new_tmdb_id
            movie.save()
            updated_count += 1
    
    print(f"Updated {updated_count} movies with proper TMDb IDs")

def import_tags():
    """Import tags from tags.csv (optional - can be used for recommendations)"""
    print("Importing tags from tags.csv...")
    tags_file = "data/ml-20m/tags.csv"
    
    # This is just for demonstration - tags aren't in the current model
    # You might want to create a Tag model later
    tag_count = 0
    with open(tags_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            tag_count += 1
    
    print(f"Found {tag_count} tags (not imported into database - no Tag model)")

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
    User.objects.filter(username='test_user', is_staff=False, is_superuser=False).delete()

    # Reset auto-increment counters
    print("Resetting auto-increment counters for tables...")
    with connection.cursor() as cursor:
        db_vendor = connection.vendor
        if db_vendor == 'sqlite':
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('recommender_movie', 'recommender_rating', 'recommender_watchlist', 'auth_user');")
        elif db_vendor == 'postgresql':
            # Note: This will also reset the user ID sequence.
            # Be careful if you have important users you don't want to affect.
            # The user deletion logic above should protect staff/superusers.
            cursor.execute("TRUNCATE TABLE recommender_watchlist, recommender_rating, recommender_movie RESTART IDENTITY CASCADE;")
            # We handle auth_user separately to avoid truncating staff/superusers
            # This is more complex in PostgreSQL to reset if not empty, but deletion handles the test users.
            # For a full reset including users, a more direct approach might be needed if non-test users are created.
        elif db_vendor == 'mysql':
            cursor.execute("TRUNCATE TABLE recommender_watchlist;")
            cursor.execute("TRUNCATE TABLE recommender_rating;")
            cursor.execute("TRUNCATE TABLE recommender_movie;")
            # Be cautious with truncating auth_user in MySQL
        else:
            print(f"Warning: Auto-increment reset not implemented for database vendor: {db_vendor}")
    
    print("Existing data cleared successfully")

@transaction.atomic
def main():
    """Main function to import all CSV data"""
    print("Starting CSV data import...")
    
    print("Step 0: Clearing existing data...")
    clear_existing_data()
    
    print("Step 1: Importing movies...")
    import_movies()
    
    print("Step 2: Importing links and updating TMDb IDs...")
    import_links()
    
    print("Step 3: Importing ratings...")
    import_ratings()
    
    print("Step 4: Analyzing tags data...")
    import_tags()
    
    print("Step 5: Creating test user...")
    create_test_user()
    
    print("\nCSV data import completed successfully!")
    print(f"Total movies in database: {Movie.objects.count()}")
    print(f"Total ratings in database: {Rating.objects.count()}")
    print(f"Total users in database: {User.objects.count()}")

if __name__ == '__main__':
    main()
