from django.db.models import prefetch_related_objects

from search.models import SavedSearch
from search.queries import published_events
from search.services import MatchService

from .models import Notification


def should_notify(user):
    preference = getattr(user, "preference", None)
    if preference is None:
        return True
    return preference.notifications_enabled


class NotificationService:
    #通知の作成・既読管理を行うサービス。本人だけが自分の通知を閲覧・既読化できる。
    @staticmethod
    def create_notification(
        *, user, event, saved_search, message,
        notification_type=Notification.NotificationType.MATCH,
    ):
        notification, _created = Notification.objects.get_or_create(
            user=user,
            event=event,
            saved_search=saved_search,
            defaults={
                "message": message,
                "notification_type": notification_type,
            },
        )
        return notification

    @staticmethod
    def mark_as_read(*, notification, user):
        if notification.user != user:
            raise PermissionError("この通知を既読にする権限がありません。")
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return notification

    @staticmethod
    def mark_all_as_read(*, user):
        return Notification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def get_notifications(*, user):
        return Notification.objects.filter(user=user)

    @staticmethod
    def unread_count(*, user):
        return Notification.objects.filter(user=user, is_read=False).count()


class EventMatchNotifier:
    #イベント公開・更新時に、条件が一致する保存検索の持ち主へ通知を作成する。
    @staticmethod
    def notify_for_event(event):
        created_notifications = []

        # event側のタグは全saved_searchで共通なので、ループに入る前に1回だけ
        # キャッシュを温めておく(MatchService.matchesはevent.tags.all()を使うため、
        # ここでprefetchしておけばsaved_search件数分の再クエリを防げる)。
        prefetch_related_objects([event], "tags")

        saved_searches = SavedSearch.objects.filter(
            notify_enabled=True
        ).select_related("owner").prefetch_related("tags")

        for saved_search in saved_searches:
            if not should_notify(saved_search.owner):
                continue
            if not MatchService.matches(saved_search, event):
                continue

            notification, created = Notification.objects.get_or_create(
                user=saved_search.owner,
                event=event,
                saved_search=saved_search,
                defaults={
                    "message": EventMatchNotifier._message_for(
                        saved_search=saved_search,
                        event=event,
                    ),
                    "notification_type": Notification.NotificationType.MATCH,
                },
            )
            if created:
                created_notifications.append(notification)

        return created_notifications

    @staticmethod
    def notify_for_saved_search(saved_search):
        """通知設定を保存した時点で、既存の公開イベントも照合する。"""
        if not saved_search.notify_enabled or not should_notify(saved_search.owner):
            return []

        prefetch_related_objects([saved_search], "tags")
        created_notifications = []

        for event in published_events().prefetch_related("tags"):
            if not MatchService.matches(saved_search, event):
                continue

            notification, created = Notification.objects.get_or_create(
                user=saved_search.owner,
                event=event,
                saved_search=saved_search,
                defaults={
                    "message": EventMatchNotifier._message_for(
                        saved_search=saved_search,
                        event=event,
                    ),
                    "notification_type": Notification.NotificationType.MATCH,
                },
            )
            if created:
                created_notifications.append(notification)

        return created_notifications

    @staticmethod
    def _message_for(*, saved_search, event):
        if saved_search.source == SavedSearch.Source.PREFERENCE:
            conditions = []
            if saved_search.location:
                conditions.append(saved_search.location)
            tag_names = [tag.name for tag in saved_search.tags.all()]
            conditions.extend(tag_names)
            summary = "・".join(conditions) or event.title
            return f"設定した「{summary}」に一致する新着イベントが見つかりました。"

        return (
            f"「{saved_search.keyword or event.title}」の条件に"
            "一致するイベントが見つかりました。"
        )
