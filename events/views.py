from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.utils import get_safe_next_url
from .models import Event
from interactions.models import EventView, Favorite, Like, Rating
from interactions.services import InteractionService
from .services import EventService


def _resolve_back_navigation(request):
    """'next' を検証し、遷移先URLと戻るリンクのラベルを算出する。"""
    next_url = get_safe_next_url(request, default="") or reverse("core:home")

    next_path = urlparse(next_url).path
    if next_path == reverse("core:home"):
        return next_url, "ホームへ戻る"
    if next_path == reverse("search:search_results"):
        return next_url, "検索結果へ戻る"
    return next_url, "前のページに戻る"


def event_detail(request, pk):
    event_filter = Q(status=Event.Status.PUBLISH)
    if request.user.is_authenticated and request.user.is_organizer:
        event_filter |= Q(organizer=request.user)

    event = get_object_or_404(
        Event.objects.filter(event_filter)
        .select_related("organizer")
        .prefetch_related("tags", "ratings__user"),
        pk=pk,
    )
    stats = InteractionService.get_event_stats(event)

    is_favorited = False
    is_liked = False
    user_rating = None
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(event=event, user=request.user).exists()
        is_liked = Like.objects.filter(event=event, user=request.user).exists()
        user_rating = Rating.objects.filter(event=event, user=request.user).first()
        InteractionService.record_view(event=event, user=request.user)

    next_url, back_label = _resolve_back_navigation(request)

    context = {
        "event": event,
        "stats": stats,
        "is_favorited": is_favorited,
        "is_liked": is_liked,
        "ratings": event.ratings.select_related("user"),
        "user_rating": user_rating,
        "rating_choices": range(5, -1, -1),
        "next_url": next_url,
        "back_label": back_label,
    }
    return render(request, "events/event_detail.html", context)

@login_required
def my_favorites(request):
    events = EventService.with_rating_summary(
        EventService.get_published_events()
        .filter(favorites__user=request.user)
        .select_related("organizer")
        .prefetch_related("tags")
    ).order_by("start_datetime")
    return render(request, "events/my_favorites.html", {"events": events})

@login_required
def my_view_history(request):
    views = (
        EventView.objects.filter(
            user=request.user,
            event__status=Event.Status.PUBLISH,
        )
        .select_related("event", "event__organizer")
        .prefetch_related("event__tags")
        .order_by("-viewed_at")
    )
    return render(request, "events/my_view_history.html", {"views": views})


@login_required
def my_organized_events(request):
    if not request.user.is_organizer:
        raise PermissionDenied("このページは主催者アカウントのみ利用できます。")

    events = EventService.with_rating_summary(
        Event.objects.filter(organizer=request.user)
        .prefetch_related("tags")
    ).order_by("-start_datetime", "pk")
    return render(request, "organizer_events.html", {"events": events})
