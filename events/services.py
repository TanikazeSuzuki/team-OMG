from django.db.models import Avg, Count

from .models import Event


class EventService:
    @staticmethod
    def get_published_events():
        return Event.objects.filter(status=Event.Status.PUBLISH)

    @staticmethod
    def with_rating_summary(queryset):
        return queryset.annotate(
            average_rating=Avg("ratings__rating"),
            review_count=Count("ratings", distinct=True),
        )

    @staticmethod
    def create_event(*, organizer, **fields):
        event = Event(organizer=organizer, **fields)
        event.full_clean()
        event.save()
        return event

    @staticmethod
    def update_event(*, event, user, **fields):
        if not (user == event.organizer or user.is_staff):
            raise PermissionError("このイベントを編集する権限がありません。")
        for field_name, value in fields.items():
            setattr(event, field_name, value)
        event.full_clean()
        event.save()
        return event

    @staticmethod
    def delete_event(*, event, user):
        if not (user == event.organizer or user.is_staff):
            raise PermissionError("このイベントを削除する権限がありません。")
        event.delete()
