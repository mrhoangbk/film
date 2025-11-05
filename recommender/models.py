from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=100)
    director = models.CharField(max_length=255)
    release_year = models.IntegerField()
    overview = models.TextField()
    poster_url = models.URLField(max_length=500, blank=True, null=True)
    tmdb_id = models.IntegerField(unique=True)
    
    def __str__(self):
        return self.title
    
    def get_first_genre(self):
        """Get the first genre from the genre string"""
        if self.genre and '|' in self.genre:
            return self.genre.split('|')[0]
        return self.genre or "Không rõ"
    
    def get_rating_display(self):
        """Get formatted rating display"""
        from django.db.models import Avg
        avg_rating = self.rating_set.aggregate(Avg('rating'))['rating__avg']
        if avg_rating:
            return f"{avg_rating:.1f}/5.0"
        return "Chưa có đánh giá"
    
    def get_genres_list(self):
        """Get list of genres from the genre string"""
        if self.genre and '|' in self.genre:
            return [g.strip() for g in self.genre.split('|')]
        elif self.genre:
            return [self.genre]
        return ["Không rõ"]


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    rating = models.FloatField()  # Will be validated to 1.0-5.0 in forms/admin
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.movie.title}: {self.rating}"
    
    class Meta:
        unique_together = ('user', 'movie')  # Prevent duplicate ratings


class Watchlist(models.Model):
    """User's watchlist for movies they want to watch later"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s watchlist - {self.movie.title}"
    
    class Meta:
        unique_together = ('user', 'movie')  # Prevent duplicate entries
        ordering = ['-added_at']
