from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

# Create your models here.

class Tag(models.Model):
    #イベントに付けるタグ（例: 「屋外」「水遊び」など）
    name = models.CharField(max_length = 50,unique = True)

    def __str__(self):
        return self.name


class Event(models.Model):
    #イベント本体のモデル。主催者が作成し、参加者が閲覧・お気に入り・評価する対象
    class Status(models.TextChoices):
        #公開状態の選択肢。下書き・中止は公開一覧に出さない（EventServiceでフィルタする）
        DRAFT = "draft" , "下書き"
        PUBLISH = "publish" , "公開"
        CANCEL = "cancel" , "中止"

    title = models.CharField(max_length = 100)
    description = models.TextField(blank=True)

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE,
        related_name = "events",
    )

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    location = models.CharField(max_length = 255, blank = True)
    official_url = models.URLField(blank=True)

    # 対象年齢の範囲。任意項目（未指定=年齢制限なし）
    min_age = models.PositiveIntegerField(null = True, blank = True)
    max_age = models.PositiveIntegerField(null = True,blank = True)

    # イベントの見出し画像。Pillowライブラリが必要（requirements.txtに追加済み）
    image = models.ImageField(upload_to="event_images/",blank = True,null = True)

    status = models.CharField(
        max_length = 10,
        choices = Status.choices,
        default = Status.DRAFT,
    )

    # タグとの多対多関係。中間テーブルとしてEventTagを明示的に使う
    # （重複防止のDB制約をEventTag側に持たせるため、throughで指定している）
    tags = models.ManyToManyField(Tag, through = "EventTag" , related_name = "events")

    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        ordering = ["-start_datetime"]  # デフォルトで開催日時が新しい順に並べる

    def __str__(self):
        return self.title

    def clean(self):
        #終了日時は開始日時より後でなければならない
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError("終了日時は開始日時より後にしてください。")

        #最低年齢は最高年齢以下でなければならない
        if self.min_age is not None and self.max_age is not None:
            if self.min_age > self.max_age:
                raise ValidationError("最低年齢は最高年齢以下にしてください。")

    @property
    def is_finished(self):
        return timezone.now() >= self.end_datetime


class EventTag(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [
        # 同じイベントに同じタグを二重登録できないようにDBレベルで制約する
            models.UniqueConstraint(
                fields=["event", "tag"], name="unique_event_tag"
            )
        ]

    def __str__(self):
        return f"{self.event.title} - {self.tag.name}"
