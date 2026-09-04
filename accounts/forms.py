from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from events.models import Tag
from search.services import SavedSearchService

from .models import User, UserPreference


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "autofocus": True,
                "placeholder": "example@example.com",
            }
        ),
    )
    password = forms.CharField(
        label="パスワード",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "name", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "name")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています。")
        return email


class UserPreferenceForm(forms.ModelForm):
    notification_tags = forms.ModelMultipleChoiceField(
        label="通知するタグ",
        queryset=Tag.objects.order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="選択したいずれかのタグと開催地の両方に合うイベントを通知します。",
    )

    class Meta:
        model = UserPreference
        fields = ("desired_location", "notifications_enabled")
        labels = {
            "desired_location": "通知する開催地",
        }
        help_texts = {
            "desired_location": "例：東京都、大阪市。イベントの開催地に部分一致します。",
            "notifications_enabled": "開催地・タグに一致した新着イベントを通知します。",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            (
                "desired_location",
                "notification_tags",
                "notifications_enabled",
            )
        )

        if self.instance and self.instance.user_id:
            saved_search = SavedSearchService.get_notification_preference(
                owner=self.instance.user
            )
            if saved_search is not None:
                self.initial["notification_tags"] = saved_search.tags.all()

    def save(self, commit=True):
        preference = super().save(commit=commit)
        if commit:
            saved_search = SavedSearchService.sync_notification_preference(
                owner=preference.user,
                location=preference.desired_location,
                tag_ids=self.cleaned_data["notification_tags"].values_list(
                    "pk", flat=True
                ),
                notify_enabled=preference.notifications_enabled,
            )
            if saved_search is not None:
                # 設定保存前から存在するイベントも、その場で照合して通知へ反映する。
                from notifications.services import EventMatchNotifier

                EventMatchNotifier.notify_for_saved_search(saved_search)
        return preference


class AccountDeletionForm(forms.Form):
    password = forms.CharField(label="現在のパスワード", widget=forms.PasswordInput)
    confirmation = forms.BooleanField(label="アカウント削除に同意します")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("パスワードが正しくありません。")
        return password
