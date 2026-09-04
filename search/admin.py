from django.contrib import admin
from .models import SavedSearch
# Register your models here.

@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "source",
        "keyword",
        "location",
        "notify_enabled",
        "created_at",
    )
    list_filter = ("source", "notify_enabled")
    search_fields = ("keyword", "location")
