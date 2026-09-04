from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.utils import get_safe_next_url
from events.models import Event
from .models import Favorite, Like, Rating
from .services import InteractionService


def _validation_message(error):
    return " ".join(error.messages)


def _redirect_to_event_detail(request, pk):
    url = reverse("events:event_detail", kwargs={"pk": pk})
    next_url = get_safe_next_url(request, default="")
    if next_url:
        url = f"{url}?{urlencode({'next': next_url})}"
    return redirect(url)


@login_required
@require_POST
def toggle_favorite(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISH)
    try:
        if Favorite.objects.filter(event=event, user=request.user).exists():
            InteractionService.remove_favorite(event=event, user=request.user)
            messages.success(request, "お気に入りから削除しました。")
        else:
            InteractionService.add_favorite(event=event, user=request.user)
            messages.success(request, "お気に入りに追加しました。")
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    return _redirect_to_event_detail(request, pk)


@login_required
@require_POST
def toggle_like(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISH)
    try:
        if Like.objects.filter(event=event, user=request.user).exists():
            InteractionService.remove_like(event=event, user=request.user)
            messages.success(request, "いいねを取り消しました。")
        else:
            InteractionService.add_like(event=event, user=request.user)
            messages.success(request, "イベントにいいねしました。")
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    return _redirect_to_event_detail(request, pk)


@login_required
@require_POST
def submit_review(request, pk):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISH)
    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "")

    try:
        InteractionService.submit_review(
            event=event, user=request.user, rating=rating, comment=comment
        )
        messages.success(request, "評価・レビューを投稿しました。")
    except ValidationError as error:
        messages.error(request, _validation_message(error))

    return _redirect_to_event_detail(request, pk)


@login_required
@require_POST
def update_rating(request, pk, rating_id):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISH)
    rating_record = get_object_or_404(Rating, pk=rating_id, event=event)

    try:
        InteractionService.update_review(
            review=rating_record,
            user=request.user,
            rating=request.POST.get("rating"),
            comment=request.POST.get("comment", ""),
        )
        messages.success(request, "評価・レビューを更新しました。")
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    except PermissionError as error:
        messages.error(request, str(error))

    return _redirect_to_event_detail(request, pk)


@login_required
@require_POST
def delete_rating(request, pk, rating_id):
    event = get_object_or_404(Event, pk=pk, status=Event.Status.PUBLISH)
    rating_record = get_object_or_404(Rating, pk=rating_id, event=event)

    try:
        InteractionService.delete_review(review=rating_record, user=request.user)
        messages.success(request, "評価・レビューを削除しました。")
    except PermissionError as error:
        messages.error(request, str(error))

    return _redirect_to_event_detail(request, pk)
