from django.shortcuts import render
from django.utils import timezone

from events.services import EventService


def home(request):
    featured_events = EventService.with_rating_summary(
        EventService.get_published_events()
        .filter(end_datetime__gte=timezone.now())
        .select_related("organizer")
        .prefetch_related("tags")
    ).order_by("start_datetime")[:6]
    return render(request, "core/home.html", {"featured_events": featured_events})
