from django.conf import settings
from django.db import models

# Create your models here.

class Notification(models.Model):
    #保存検索の条件に一致した公開イベントについてユーザーへ届く通知。
    class NotificationType(models.TextChoices):
        #暫定でマッチ通知のみ。将来の種別追加に備えてchoicesにしている。
        MATCH = "match", "条件一致"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    saved_search = models.ForeignKey(
        "search.SavedSearch",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.MATCH,
    )
    message = models.CharField(max_length=255)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # 同じユーザー・イベント・保存条件の組み合わせで通知を二重生成しない
            models.UniqueConstraint(
                fields=["user", "event", "saved_search"],
                name="uniq_match_notification",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.event.title}"
