from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from .models import Movie, Rating, Watchlist
from .forms import RatingForm
from .recommender_engine import HybridRecommender


def home(request):
    """Trang chủ kiểu Netflix với các hàng phim và carousel"""
    # Lấy phim được đánh giá cao nhất (theo điểm trung bình)
    top_rated_movies = Movie.objects.annotate(
        avg_rating=Avg('rating__rating')
    ).filter(avg_rating__isnull=False).order_by('-avg_rating')[:20]
    
    # Lấy phim phổ biến (theo số lượng đánh giá) và thêm điểm trung bình
    popular_movies = Movie.objects.annotate(
        rating_count=Count('rating'),
        avg_rating=Avg('rating__rating')
    ).filter(rating_count__gt=0).order_by('-rating_count')[:20]
    
    # Lấy phim đề xuất cho người dùng đã đăng nhập
    recommended_movies = []
    if request.user.is_authenticated:
        try:
            recommender = HybridRecommender()
            recommended_movie_ids = recommender.get_recommendations(
                user_id=request.user.id, 
                n=20
            )
            recommended_movies = Movie.objects.filter(id__in=recommended_movie_ids).annotate(
                avg_rating=Avg('rating__rating')
            )
        except Exception as e:
            # Fallback: sử dụng phim phổ biến nếu đề xuất thất bại
            recommended_movies = popular_movies[:10]
    
    # Lấy thể loại duy nhất cho phần duyệt
    all_genres = Movie.objects.values_list('genre', flat=True).distinct()
    unique_genres = set()
    for genre_str in all_genres:
        if genre_str:
            genres = [g.strip() for g in genre_str.split('|')]
            unique_genres.update(genres)
    
    context = {
        'top_rated_movies': top_rated_movies,
        'popular_movies': popular_movies,
        'recommended_movies': recommended_movies,
        'genres': sorted(unique_genres)[:12],  # Giới hạn 12 thể loại để hiển thị
    }
    
    return render(request, 'recommender/home.html', context)




@login_required
def rate_movie(request, movie_id):
    """Rate a movie (POST only)"""
    if request.method == 'POST':
        movie = get_object_or_404(Movie, id=movie_id)
        form = RatingForm(request.POST)
        
        if form.is_valid():
            rating_value = form.cleaned_data['rating']
            
            # Create or update rating
            rating, created = Rating.objects.update_or_create(
                user=request.user,
                movie=movie,
                defaults={'rating': rating_value}
            )
            
            if created:
                messages.success(request, f'Successfully rated "{movie.title}" with {rating_value} stars')
            else:
                messages.success(request, f'Updated rating for "{movie.title}" to {rating_value} stars')
                
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Rated {movie.title} with {rating_value} stars'
                })
            else:
                return redirect('recommender:recommendations')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            else:
                messages.error(request, 'Invalid rating value')
                return redirect('recommender:recommendations')
    
    # GET request - redirect to recommendations
    return redirect('recommender:recommendations')


def search_movie(request):
    """Search movies by title and genre"""
    query = request.GET.get('q', '')
    genre_filter = request.GET.get('genre', '')
    
    movies = Movie.objects.all()
    
    if query:
        movies = movies.filter(title__icontains=query)
    
    if genre_filter:
        movies = movies.filter(genre__icontains=genre_filter)
    
    # Get unique genres for filter dropdown
    all_genres = Movie.objects.values_list('genre', flat=True).distinct()
    unique_genres = set()
    for genre_str in all_genres:
        if genre_str:
            genres = [g.strip() for g in genre_str.split('|')]
            unique_genres.update(genres)
    
    # Pagination
    paginator = Paginator(movies, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get user ratings if logged in
    user_ratings = {}
    if request.user.is_authenticated:
        user_ratings = {
            rating.movie_id: rating.rating 
            for rating in Rating.objects.filter(user=request.user)
        }
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'genre_filter': genre_filter,
        'genres': sorted(unique_genres),
        'user_ratings': user_ratings,
    }
    
    return render(request, 'recommender/search.html', context)


@login_required
def movie_detail(request, movie_id):
    """Movie detail page with rating form"""
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Get user's rating for this movie if exists
    user_rating = None
    try:
        user_rating = Rating.objects.get(user=request.user, movie=movie)
    except Rating.DoesNotExist:
        pass
    
    # Get similar movies (content-based)
    try:
        recommender = HybridRecommender()
        movie_idx = recommender.movies_df[recommender.movies_df['id'] == movie.id].index[0]
        similar_indices = recommender.content_similarity[movie_idx].argsort()[-6:-1][::-1]
        similar_movies = []
        for idx in similar_indices:
            similar_movie_id = recommender.movies_df.iloc[idx]['id']
            similar_movie = Movie.objects.get(id=similar_movie_id)
            similar_movies.append(similar_movie)
    except Exception as e:
        similar_movies = Movie.objects.exclude(id=movie.id)[:5]
    
    context = {
        'movie': movie,
        'user_rating': user_rating,
        'similar_movies': similar_movies,
        'form': RatingForm(initial={'rating': user_rating.rating if user_rating else 3.0})
    }
    
    return render(request, 'recommender/movie_detail.html', context)


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to MovieRecommender.')
            return redirect('recommender:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile_view(request):
    """User profile page with watchlist and rating history"""
    # Get user's watchlist
    watchlist_movies = Watchlist.objects.filter(user=request.user).select_related('movie')
    
    # Get user's rating history
    rated_movies = Rating.objects.filter(user=request.user).select_related('movie').order_by('-timestamp')
    
    context = {
        'watchlist_movies': watchlist_movies,
        'rated_movies': rated_movies,
    }
    
    return render(request, 'recommender/profile.html', context)


@login_required
def add_to_watchlist(request, movie_id):
    """Add or remove movie from watchlist (AJAX)"""
    if request.method == 'POST':
        movie = get_object_or_404(Movie, id=movie_id)
        
        # Check if movie is already in watchlist
        watchlist_item, created = Watchlist.objects.get_or_create(
            user=request.user,
            movie=movie
        )
        
        if created:
            message = f'"{movie.title}" added to your watchlist'
            action = 'added'
        else:
            # Remove from watchlist if already exists
            watchlist_item.delete()
            message = f'"{movie.title}" removed from your watchlist'
            action = 'removed'
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'action': action,
                'movie_id': movie_id
            })
        else:
            messages.success(request, message)
            return redirect('recommender:movie_detail', movie_id=movie_id)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def search_api(request):
    """API endpoint for search autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'movies': []})
    
    # Cache search results for performance
    cache_key = f"search_{query}"
    cached_results = cache.get(cache_key)
    
    if cached_results:
        return JsonResponse({'movies': cached_results})
    
    # Search movies by title and genre
    movies = Movie.objects.filter(
        Q(title__icontains=query) | Q(genre__icontains=query)
    )[:10]  # Limit to 10 results for autocomplete
    
    results = []
    for movie in movies:
        results.append({
            'id': movie.id,
            'title': movie.title,
            'genre': movie.genre,
            'release_year': movie.release_year,
            'poster_url': movie.poster_url or '',
            'overview': movie.overview[:100] + '...' if len(movie.overview) > 100 else movie.overview
        })
    
    # Cache for 5 minutes
    cache.set(cache_key, results, 300)
    
    return JsonResponse({'movies': results})


def load_more(request, category):
    """API endpoint for infinite scroll loading"""
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    # Cache key based on category and page
    cache_key = f"load_more_{category}_{page}"
    cached_results = cache.get(cache_key)
    
    if cached_results:
        return JsonResponse(cached_results)
    
    # Determine which movies to load based on category
    if category == 'popular':
        movies = Movie.objects.annotate(
            rating_count=Count('rating')
        ).filter(rating_count__gt=0).order_by('-rating_count')
    elif category == 'top_rated':
        movies = Movie.objects.annotate(
            avg_rating=Avg('rating__rating')
        ).filter(avg_rating__isnull=False).order_by('-avg_rating')
    elif category == 'recommended' and request.user.is_authenticated:
        try:
            recommender = HybridRecommender()
            recommended_movie_ids = recommender.get_recommendations(
                user_id=request.user.id, 
                n=100  # Get more for pagination
            )
            movies = Movie.objects.filter(id__in=recommended_movie_ids)
        except Exception as e:
            movies = Movie.objects.all()[:100]
    else:
        movies = Movie.objects.all()
    
    # Paginate results
    paginator = Paginator(movies, page_size)
    try:
        page_obj = paginator.page(page)
    except:
        return JsonResponse({'movies': [], 'has_next': False})
    
    # Prepare movie data
    movie_data = []
    for movie in page_obj:
        movie_data.append({
            'id': movie.id,
            'title': movie.title,
            'genre': movie.genre,
            'release_year': movie.release_year,
            'poster_url': movie.poster_url or '',
            'overview': movie.overview[:150] + '...' if len(movie.overview) > 150 else movie.overview,
            'director': movie.director
        })
    
    response_data = {
        'movies': movie_data,
        'has_next': page_obj.has_next(),
        'next_page': page + 1 if page_obj.has_next() else None
    }
    
    # Cache for 10 minutes
    cache.set(cache_key, response_data, 600)
    
    return JsonResponse(response_data)




@login_required
def recommendations(request):
    """Get movie recommendations for the logged-in user"""
    try:
        recommender = HybridRecommender()
        recommended_movie_ids = recommender.get_recommendations(
            user_id=request.user.id, 
            n=20
        )
        
        # Get movie objects for hybrid recommendations with ratings
        hybrid_recommendations = Movie.objects.filter(id__in=recommended_movie_ids).annotate(
            avg_rating=Avg('rating__rating')
        )
        
        # Get user's watchlist movies as Movie objects with ratings
        watchlist_movies = Movie.objects.filter(watchlist__user=request.user).annotate(
            avg_rating=Avg('rating__rating')
        )
        
        # For the new section: recommendations for watchlist addition
        # Use hybrid_recommendations but exclude movies already in watchlist
        watchlist_movie_ids = watchlist_movies.values_list('id', flat=True)
        recommendations_for_watchlist = hybrid_recommendations.exclude(id__in=watchlist_movie_ids)
        
        context = {
            'hybrid_recommendations': hybrid_recommendations,
            'watchlist_movies': watchlist_movies,
            'recommendations_for_watchlist': recommendations_for_watchlist,
        }
        
        return render(request, 'recommender/recommendations.html', context)
        
    except Exception as e:
        messages.error(request, f"Error generating recommendations: {str(e)}")
        
        # Fallback: show popular movies with ratings
        popular_movies = Movie.objects.all()[:20].annotate(
            avg_rating=Avg('rating__rating')
        )
        watchlist_movies = Movie.objects.filter(watchlist__user=request.user).annotate(
            avg_rating=Avg('rating__rating')
        )
        
        context = {
            'hybrid_recommendations': popular_movies,
            'watchlist_movies': watchlist_movies,
        }
        
        return render(request, 'recommender/recommendations.html', context)
