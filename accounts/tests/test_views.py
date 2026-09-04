from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from events.models import Tag


class AccountViewTests(TestCase):
    def test_login_uses_email_form_and_custom_template(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertContains(response, 'type="email"')
        self.assertContains(response, "css/login.css")

    def test_login_with_email_succeeds(self):
        user = User.objects.create_user(
            email="login@example.com",
            password="SafePassword123!",
            name="ログイン確認",
        )

        response = self.client.post(
            reverse("accounts:login"),
            data={
                "username": "login@example.com",
                "password": "SafePassword123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:profile"),
            fetch_redirect_response=False,
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:profile')}",
            fetch_redirect_response=False,
        )

    def test_signup_creates_and_logs_in_user(self):
        response = self.client.post(
            reverse("accounts:signup"),
            data={
                "email": "signup@example.com",
                "name": "新規参加者",
                "role": User.Role.PARTICIPANT,
                "password1": "SafePassword123!",
                "password2": "SafePassword123!",
            },
        )

        self.assertRedirects(
            response,
            reverse("accounts:profile"),
            fetch_redirect_response=False,
        )
        self.assertTrue(User.objects.filter(email="signup@example.com").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(email="signup@example.com").pk)

    def test_account_delete_removes_user(self):
        user = User.objects.create_user(
            email="delete-success@example.com",
            password="SafePassword123!",
            name="削除成功",
        )
        user_id = user.pk
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:delete"),
            data={"password": "SafePassword123!", "confirmation": True},
        )

        self.assertRedirects(response, reverse("core:home"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=user_id).exists())

    def test_preferences_page_shows_location_and_tag_settings(self):
        user = User.objects.create_user(
            email="preference-page@example.com",
            password="SafePassword123!",
            name="設定画面確認",
        )
        Tag.objects.create(name="子ども向け")
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:preferences"))

        self.assertContains(response, "通知する開催地")
        self.assertContains(response, 'name="desired_location"')
        self.assertContains(response, 'name="notification_tags"')
        self.assertContains(response, "子ども向け")
