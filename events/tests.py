from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from interactions.models import Favorite

from .models import Event
from .services import EventService

User = get_user_model()


class EventServiceTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(email="organizer@example.com", password="pass")
        self.other_user = User.objects.create_user(email="other@example.com", password="pass")
        self.admin = User.objects.create_user(
            email="admin@example.com", password="pass", is_staff=True
        )

        self.start = timezone.now() + timedelta(days=1)
        self.end = timezone.now() + timedelta(days=2)

    def _create_event(self, **overrides):
        defaults = dict(
            title="テストイベント",
            organizer=self.organizer,
            start_datetime=self.start,
            end_datetime=self.end,
        )
        defaults.update(overrides)
        return EventService.create_event(**defaults)


    def test_create_event_success(self):
        event = self._create_event()
        self.assertEqual(event.title, "テストイベント")

    def test_create_event_end_before_start_raises_error(self):
        with self.assertRaises(ValidationError):
            self._create_event(start_datetime=self.end, end_datetime=self.start)

    def test_create_event_min_age_over_max_age_raises_error(self):
        with self.assertRaises(ValidationError):
            self._create_event(min_age=20, max_age=10)

    def test_create_event_min_age_equal_max_age_is_allowed(self):
        event = self._create_event(min_age=15, max_age=15)
        self.assertEqual(event.min_age, event.max_age)


    def test_update_event_by_organizer_success(self):
        event = self._create_event()
        updated = EventService.update_event(
            event=event, user=self.organizer, title="更新後タイトル"
        )
        self.assertEqual(updated.title, "更新後タイトル")

    def test_update_event_by_admin_success(self):
        event = self._create_event()
        updated = EventService.update_event(
            event=event, user=self.admin, title="管理者による更新"
        )
        self.assertEqual(updated.title, "管理者による更新")

    def test_update_event_by_other_user_raises_error(self):
        event = self._create_event()
        with self.assertRaises(PermissionError):
            EventService.update_event(
                event=event, user=self.other_user, title="不正な更新"
            )


    def test_delete_event_by_organizer_success(self):
        event = self._create_event()
        EventService.delete_event(event=event, user=self.organizer)
        self.assertFalse(Event.objects.filter(pk=event.pk).exists())

    def test_delete_event_by_other_user_raises_error(self):
        event = self._create_event()
        with self.assertRaises(PermissionError):
            EventService.delete_event(event=event, user=self.other_user)
        self.assertTrue(Event.objects.filter(pk=event.pk).exists())


    def test_published_events_excludes_draft_and_cancelled(self):
        published = self._create_event(title="公開イベント", status=Event.Status.PUBLISH)
        self._create_event(title="下書きイベント", status=Event.Status.DRAFT)
        self._create_event(title="中止イベント", status=Event.Status.CANCEL)

        result = EventService.get_published_events()

        self.assertIn(published, result)
        self.assertEqual(result.count(), 1)

class MyFavoritesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user1@example.com", password="pass")
        self.organizer = User.objects.create_user(email="organizer@example.com", password="pass")

        self.event = Event.objects.create(
            title="テストイベント",
            organizer=self.organizer,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
            status=Event.Status.PUBLISH,
        )
        Favorite.objects.create(event=self.event, user=self.user)

    def test_my_favorites_requires_login(self):
        response = self.client.get(reverse("events:my_favorites"))
        self.assertEqual(response.status_code, 302)

    def test_my_favorites_accessible_when_logged_in(self):
        self.client.login(email="user1@example.com", password="pass")
        response = self.client.get(reverse("events:my_favorites"))
        self.assertEqual(response.status_code, 200)


class MyViewHistoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user1@example.com", password="pass")

    def test_my_view_history_requires_login(self):
        response = self.client.get(reverse("events:my_view_history"))
        self.assertEqual(response.status_code, 302)

    def test_my_view_history_accessible_when_logged_in(self):
        self.client.login(email="user1@example.com", password="pass")
        response = self.client.get(reverse("events:my_view_history"))
        self.assertEqual(response.status_code, 200)
