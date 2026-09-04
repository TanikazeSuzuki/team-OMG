from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from events.models import Event

from .services import EventMatchNotifier


@receiver(post_save, sender=Event)
def notify_when_event_is_published(sender, instance, raw=False, **kwargs):
    """公開イベントが追加・更新された時点で一致通知を生成する。"""
    if raw or instance.status != Event.Status.PUBLISH:
        return
    EventMatchNotifier.notify_for_event(instance)


@receiver(m2m_changed, sender=Event.tags.through)
def notify_when_published_event_gets_tags(sender, instance, action, **kwargs):
    """管理画面でイベント保存後にタグが付く流れにも対応する。"""
    if action != "post_add" or instance.status != Event.Status.PUBLISH:
        return
    EventMatchNotifier.notify_for_event(instance)
