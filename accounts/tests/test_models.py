from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User, UserPreference


class UserModelTests(TestCase):
    def test_create_user_uses_email_as_login_identifier(self):
        user = User.objects.create_user(
            email="USER@EXAMPLE.COM",
            password="SafePassword123!",
            name="参加者",
        )

        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.check_password("SafePassword123!"))
        self.assertEqual(user.role, User.Role.PARTICIPANT)

    def test_email_must_be_unique(self):
        User.objects.create_user(
            email="same@example.com",
            password="SafePassword123!",
            name="1人目",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="same@example.com",
                password="SafePassword123!",
                name="2人目",
            )

    def test_preference_is_created_with_user(self):
        user = User.objects.create_user(
            email="preference@example.com",
            password="SafePassword123!",
            name="設定確認",
        )

        preference = UserPreference.objects.get(user=user)
        self.assertTrue(preference.notifications_enabled)
        self.assertEqual(preference.theme_color, UserPreference.Theme.SYSTEM)

    def test_organizer_property_accepts_organizer_and_staff(self):
        participant = User.objects.create_user(
            email="participant@example.com",
            password="SafePassword123!",
            name="参加者",
        )
        organizer = User.objects.create_user(
            email="organizer@example.com",
            password="SafePassword123!",
            name="主催者",
            role=User.Role.ORGANIZER,
        )
        staff = User.objects.create_user(
            email="staff@example.com",
            password="SafePassword123!",
            name="管理者",
            is_staff=True,
        )

        self.assertFalse(participant.is_organizer)
        self.assertTrue(organizer.is_organizer)
        self.assertTrue(staff.is_organizer)
