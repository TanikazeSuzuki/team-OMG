from django.test import TestCase

from accounts.forms import AccountDeletionForm, RegistrationForm, UserPreferenceForm
from accounts.models import User
from events.models import Tag
from search.models import SavedSearch


class RegistrationFormTests(TestCase):
    def test_valid_registration_form(self):
        form = RegistrationForm(
            data={
                "email": "user@example.com",
                "name": "参加者",
                "role": User.Role.PARTICIPANT,
                "password1": "SafePassword123!",
                "password2": "SafePassword123!",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="used@example.com",
            password="SafePassword123!",
            name="登録済み",
        )
        form = RegistrationForm(
            data={
                "email": "used@example.com",
                "name": "別ユーザー",
                "role": User.Role.PARTICIPANT,
                "password1": "SafePassword123!",
                "password2": "SafePassword123!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_duplicate_email_is_rejected_regardless_of_case(self):
        User.objects.create_user(
            email="case@example.com",
            password="SafePassword123!",
            name="登録済み",
        )
        form = RegistrationForm(
            data={
                "email": "CASE@EXAMPLE.COM",
                "name": "別ユーザー",
                "role": User.Role.PARTICIPANT,
                "password1": "SafePassword123!",
                "password2": "SafePassword123!",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class AccountDeletionFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="delete@example.com",
            password="SafePassword123!",
            name="削除対象",
        )

    def test_wrong_password_is_rejected(self):
        form = AccountDeletionForm(
            user=self.user,
            data={"password": "wrong", "confirmation": True},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)


class UserPreferenceFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="preference-form@example.com",
            password="SafePassword123!",
            name="通知設定確認",
        )
        self.outdoor = Tag.objects.create(name="屋外")
        self.free = Tag.objects.create(name="無料")

    def test_save_syncs_location_and_tags_to_notification_search(self):
        form = UserPreferenceForm(
            instance=self.user.preference,
            data={
                "desired_location": "東京都",
                "notification_tags": [self.outdoor.pk, self.free.pk],
                "notifications_enabled": "on",
                "theme_color": "system",
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        saved_search = SavedSearch.objects.get(
            owner=self.user,
            source=SavedSearch.Source.PREFERENCE,
        )
        self.assertEqual(saved_search.location, "東京都")
        self.assertTrue(saved_search.notify_enabled)
        self.assertSetEqual(
            set(saved_search.tags.values_list("pk", flat=True)),
            {self.outdoor.pk, self.free.pk},
        )

    def test_clearing_location_and_tags_removes_notification_search(self):
        SavedSearch.objects.create(
            owner=self.user,
            source=SavedSearch.Source.PREFERENCE,
            location="東京都",
        )
        form = UserPreferenceForm(
            instance=self.user.preference,
            data={
                "desired_location": "",
                "notification_tags": [],
                "notifications_enabled": "on",
                "theme_color": "system",
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertFalse(
            SavedSearch.objects.filter(
                owner=self.user,
                source=SavedSearch.Source.PREFERENCE,
            ).exists()
        )
