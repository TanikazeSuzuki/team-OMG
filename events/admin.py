from django.contrib import admin
from .models import Event, Tag, EventTag
# Register your models here.

class EventTagInline(admin.TabularInline):
    model = EventTag
    extra = 1

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "status", "start_datetime", "end_datetime")
    list_filter = ("status",)
    search_fields = ("title", "description")
    inlines = [EventTagInline]

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)