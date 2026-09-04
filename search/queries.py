from events.models import Event


def published_events():
    """検索・通知の対象となる公開イベントのみを返す（下書き・中止イベントを除外）。"""
    return Event.objects.exclude(status__in=[Event.Status.DRAFT, Event.Status.CANCEL])
