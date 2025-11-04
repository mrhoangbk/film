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


class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    rating = models.FloatField()  # Will be validated to 1.0-5.0 in forms/admin
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.movie.title}: {self.rating}"
    
    class Meta:
        unique_together = ('user', 'movie')  # Prevent duplicate ratings
