from django.contrib import admin
from .models import Movie, Rating


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'director', 'release_year', 'tmdb_id')
    list_filter = ('genre', 'release_year')
    search_fields = ('title', 'director')
    ordering = ('title',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'rating', 'timestamp')
    list_filter = ('rating', 'timestamp')
    search_fields = ('user__username', 'movie__title')
    ordering = ('-timestamp',)
