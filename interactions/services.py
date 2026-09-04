from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Avg, Count

from .models import Favorite, Like, EventView, Rating


class InteractionService:
    @staticmethod
    def add_favorite(*, event, user):
        if Favorite.objects.filter(event=event, user=user).exists():
            raise ValidationError("すでにお気に入り登録済みです。")
        try:
            return Favorite.objects.create(event=event, user=user)
        except IntegrityError:
            raise ValidationError("すでにお気に入り登録済みです。")

    @staticmethod
    def remove_favorite(*, event, user):
        deleted, _ = Favorite.objects.filter(event=event, user=user).delete()
        if deleted == 0:
            raise ValidationError("お気に入り登録されていません。")

    @staticmethod
    def add_like(*, event, user):
        if Like.objects.filter(event=event, user=user).exists():
            raise ValidationError("すでにいいね済みです。")
        try:
            return Like.objects.create(event=event, user=user)
        except IntegrityError:
            raise ValidationError("すでにいいね済みです。")

    @staticmethod
    def remove_like(*, event, user):
        deleted, _ = Like.objects.filter(event=event, user=user).delete()
        if deleted == 0:
            raise ValidationError("いいねされていません。")

    @staticmethod
    def record_view(*, event, user):
        return EventView.objects.create(event=event, user=user)

    @staticmethod
    def submit_review(*, event, user, rating, comment=None):
        if Rating.objects.filter(event=event, user=user).exists():
            raise ValidationError("すでに評価・レビュー済みです。編集はupdate_reviewを使ってください。")
        
        review = Rating(event=event, user=user, rating=rating, comment=comment)
        review.full_clean()
        review.save()
        return review

    @staticmethod
    def update_review(*, review, user, rating=None, comment=None):
        if not (user == review.user or user.is_staff):
            raise PermissionError("このレビューを編集する権限がありません。")

        if rating is not None:
            review.rating = rating
        if comment is not None:
            review.comment = comment

        review.full_clean()
        review.save()
        return review

    @staticmethod
    def delete_review(*, review, user):
        if not (user == review.user or user.is_staff):
            raise PermissionError("このレビューを削除する権限がありません。")
        review.delete()

    @staticmethod
    def get_event_stats(event):
        review_stats = event.ratings.aggregate(
            average_rating=Avg("rating"),
            review_count=Count("id"),
        )
        return {
            "average_rating": review_stats["average_rating"] or 0,
            "review_count": review_stats["review_count"],
            "favorite_count": event.favorites.count(),
            "like_count": event.likes.count(),
        }