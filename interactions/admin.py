from django.contrib import admin
from .models import Favorite, Like, EventView, Rating

# Register your models here.

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "created_at")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "created_at")


@admin.register(EventView)
class EventViewAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "viewed_at")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "rating", "created_at")
    list_filter = ("rating",)
# Register your models here.
