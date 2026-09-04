from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.

class SavedSearch(models.Model):
    #ユーザーが保存した検索条件。一致する新着イベントの通知トリガーとなる。
    class Source(models.TextChoices):
        MANUAL = "manual", "検索画面"
        PREFERENCE = "preference", "通知設定"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_searches",
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )

    keyword = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)

    # 検索対象の開催期間。任意項目（未指定=期間制限なし）
    period_from = models.DateField(null=True, blank=True)
    period_to = models.DateField(null=True, blank=True)

    # 旧バージョンとのDB互換性用。検索・通知の判定には使用しない。
    age_min = models.PositiveIntegerField(null=True, blank=True)
    age_max = models.PositiveIntegerField(null=True, blank=True)

    tags = models.ManyToManyField(
        "events.Tag", blank=True, related_name="saved_searches"
    )

    # MVPでは未使用。優先度付けが必要になった場合に備えたフリーテキスト項目
    # （選択肢はまだ確定していないためchoicesは固定しない）。
    priority = models.CharField(max_length=20, blank=True)

    notify_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(source="preference"),
                name="unique_preference_search_per_user",
            )
        ]

    def __str__(self):
        return f"{self.owner} - {self.keyword or '(キーワードなし)'}"

    def clean(self):
        #検索期間の開始は終了以前でなければならない
        if self.period_from and self.period_to:
            if self.period_from > self.period_to:
                raise ValidationError("検索期間の開始日は終了日以前にしてください。")

        #対象年齢の下限は上限以下でなければならない
        if self.age_min is not None and self.age_max is not None:
            if self.age_min > self.age_max:
                raise ValidationError("対象年齢の下限は上限以下にしてください。")
