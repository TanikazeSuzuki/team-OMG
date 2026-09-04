from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("mine/favorites/", views.my_favorites, name="my_favorites"),
    path("mine/history/", views.my_view_history, name="my_view_history"),
    path("mine/organized/", views.my_organized_events, name="my_organized_events"),
    path("<int:pk>/", views.event_detail, name="event_detail"),
]
