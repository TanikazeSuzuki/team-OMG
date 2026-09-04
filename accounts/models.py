from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("メールアドレスは必須です。")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("スーパーユーザーは is_staff=True である必要があります。")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("スーパーユーザーは is_superuser=True である必要があります。")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        PARTICIPANT = "participant", "一般参加者"
        ORGANIZER = "organizer", "主催者"

    username = None
    email = models.EmailField("メールアドレス", unique=True)
    name = models.CharField("表示名", max_length=150)
    role = models.CharField(
        "ユーザー種別",
        max_length=20,
        choices=Role.choices,
        default=Role.PARTICIPANT,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.name or self.email

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email).strip().lower()
        return super().save(*args, **kwargs)

    @property
    def is_organizer(self):
        return self.role == self.Role.ORGANIZER or self.is_staff


class UserPreference(models.Model):
    class Theme(models.TextChoices):
        SYSTEM = "system", "端末設定に合わせる"
        LIGHT = "light", "ライト"
        DARK = "dark", "ダーク"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preference",
    )
    desired_location = models.CharField("希望地域", max_length=255, blank=True)
    notifications_enabled = models.BooleanField("通知を受け取る", default=True)
    theme_color = models.CharField(
        "テーマ",
        max_length=20,
        choices=Theme.choices,
        default=Theme.SYSTEM,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ユーザー設定"
        verbose_name_plural = "ユーザー設定"

    def __str__(self):
        return f"{self.user} の設定"
