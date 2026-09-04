from django.test import TestCase

from accounts.models import User, UserPreference
from accounts.services import AccountService


class AccountServiceTests(TestCase):
    def test_create_account_creates_preference(self):
        user = AccountService.create_account(
            email="service@example.com",
            password="SafePassword123!",
            name="サービス作成",
        )

        self.assertTrue(UserPreference.objects.filter(user=user).exists())

    def test_delete_account_removes_user_and_preference(self):
        user = AccountService.create_account(
            email="delete-service@example.com",
            password="SafePassword123!",
            name="削除対象",
        )
        user_id = user.pk

        AccountService.delete_account(user)

        self.assertFalse(User.objects.filter(pk=user_id).exists())
        self.assertFalse(UserPreference.objects.filter(user_id=user_id).exists())
