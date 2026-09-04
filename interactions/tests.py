import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from events.models import Event
from .models import Favorite
from .services import InteractionService

User = get_user_model()


class InteractionServiceTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(email="organizer@example.com", password="pass")
        self.user = User.objects.create_user(email="user1@example.com", password="pass")
        self.other_user = User.objects.create_user(email="user2@example.com", password="pass")

        self.finished_event = Event.objects.create(
            title="終了済みイベント",
            organizer=self.organizer,
            start_datetime=timezone.now() - timedelta(days=2),
            end_datetime=timezone.now() - timedelta(days=1),
            status=Event.Status.PUBLISH,
        )

        self.upcoming_event = Event.objects.create(
            title="開催前イベント",
            organizer=self.organizer,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
            status=Event.Status.PUBLISH,
        )


    def test_add_favorite_success(self):
        InteractionService.add_favorite(event=self.finished_event, user=self.user)
        self.assertTrue(
            Favorite.objects.filter(event=self.finished_event, user=self.user).exists()
        )

    def test_add_favorite_duplicate_raises_error(self):
        InteractionService.add_favorite(event=self.finished_event, user=self.user)
        with self.assertRaises(ValidationError):
            InteractionService.add_favorite(event=self.finished_event, user=self.user)

    def test_remove_favorite_success(self):
        InteractionService.add_favorite(event=self.finished_event, user=self.user)
        InteractionService.remove_favorite(event=self.finished_event, user=self.user)
        self.assertFalse(
            Favorite.objects.filter(event=self.finished_event, user=self.user).exists()
        )

    def test_remove_favorite_not_registered_raises_error(self):
        with self.assertRaises(ValidationError):
            InteractionService.remove_favorite(event=self.finished_event, user=self.user)


    def test_add_like_duplicate_raises_error(self):
        InteractionService.add_like(event=self.finished_event, user=self.user)
        with self.assertRaises(ValidationError):
            InteractionService.add_like(event=self.finished_event, user=self.user)


    def test_submit_review_before_event_finished_raises_error(self):
        """開催前(終了前)のイベントには評価・レビューできないこと"""
        with self.assertRaises(ValidationError):
            InteractionService.submit_review(
                event=self.upcoming_event, user=self.user, rating=5
            )

    def test_submit_review_after_event_finished_success(self):
        review = InteractionService.submit_review(
            event=self.finished_event, user=self.user, rating=5
        )
        self.assertEqual(review.rating, 5)

    def test_submit_review_rating_out_of_range_raises_error(self):
        with self.assertRaises(ValidationError):
            InteractionService.submit_review(
                event=self.finished_event, user=self.user, rating=6
            )

    def test_submit_review_rating_zero_is_allowed(self):
        review = InteractionService.submit_review(
            event=self.finished_event, user=self.user, rating=0
        )
        self.assertEqual(review.rating, 0)

    def test_submit_review_duplicate_raises_error(self):
        InteractionService.submit_review(event=self.finished_event, user=self.user, rating=3)
        with self.assertRaises(ValidationError):
            InteractionService.submit_review(
                event=self.finished_event, user=self.user, rating=4
            )

    def test_update_review_by_owner_success(self):
        review = InteractionService.submit_review(
            event=self.finished_event, user=self.user, rating=3
        )
        updated = InteractionService.update_review(review=review, user=self.user, rating=5)
        self.assertEqual(updated.rating, 5)

    def test_update_review_by_other_user_raises_error(self):
        """他人のレビューは編集できないこと"""
        review = InteractionService.submit_review(
            event=self.finished_event, user=self.user, rating=3
        )
        with self.assertRaises(PermissionError):
            InteractionService.update_review(review=review, user=self.other_user, rating=5)

    def test_delete_review_by_other_user_raises_error(self):
        review = InteractionService.submit_review(
            event=self.finished_event, user=self.user, rating=3
        )
        with self.assertRaises(PermissionError):
            InteractionService.delete_review(review=review, user=self.other_user)


    def test_get_event_stats_calculates_correctly(self):
        InteractionService.submit_review(event=self.finished_event, user=self.user, rating=4)
        InteractionService.submit_review(
            event=self.finished_event, user=self.other_user, rating=2
        )
        InteractionService.add_favorite(event=self.finished_event, user=self.user)

        stats = InteractionService.get_event_stats(self.finished_event)

        self.assertEqual(stats["review_count"], 2)
        self.assertEqual(stats["average_rating"], 3.0)  # (4+2)/2
        self.assertEqual(stats["favorite_count"], 1)


class RedirectNextParameterTests(TestCase):
    #POSTアクション後のリダイレクトが 'next' を正しく引き継ぐ・拒否することを検証する。
    def setUp(self):
        self.organizer = User.objects.create_user(
            email="redirect-organizer@example.com", password="pass12345"
        )
        self.user = User.objects.create_user(
            email="redirect-user@example.com", password="pass12345"
        )
        self.event = Event.objects.create(
            title="リダイレクト確認イベント",
            organizer=self.organizer,
            start_datetime=timezone.now() - timedelta(days=2),
            end_datetime=timezone.now() - timedelta(days=1),
            status=Event.Status.PUBLISH,
        )
        self.client.force_login(self.user)
        self.favorite_url = reverse("interactions:toggle_favorite", args=[self.event.pk])
        self.detail_url = reverse("events:event_detail", args=[self.event.pk])

    def test_toggle_favorite_without_next_redirects_to_plain_detail_url(self):
        response = self.client.post(self.favorite_url)

        self.assertRedirects(response, self.detail_url)

    def test_toggle_favorite_rejects_absolute_hostile_next(self):
        response = self.client.post(
            self.favorite_url, {"next": "https://evil.example.com/"}
        )

        self.assertRedirects(response, self.detail_url)
        self.assertNotIn("evil.example.com", response["Location"])

    def test_toggle_favorite_rejects_protocol_relative_hostile_next(self):
        response = self.client.post(
            self.favorite_url, {"next": "//evil.example.com"}
        )

        self.assertRedirects(response, self.detail_url)
        self.assertNotIn("evil.example.com", response["Location"])

    def test_toggle_favorite_round_trips_next_across_two_hops(self):
        target_next = "/search/?keyword=花火&sort=newest"

        response = self.client.post(self.favorite_url, {"next": target_next})

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith(self.detail_url + "?next="))

        # 1ホップ目: リダイレクト先の詳細ページを実際にGETする。
        detail_response = self.client.get(location)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.context["next_url"], target_next)
        self.assertContains(detail_response, "← 検索結果へ戻る")

        back_match = re.search(
            r'class="back-link" href="([^"]+)"', detail_response.content.decode()
        )
        self.assertIsNotNone(back_match)
        back_href = back_match.group(1).replace("&amp;", "&")
        self.assertEqual(back_href, target_next)

        # 2ホップ目: 詳細ページ自身の戻りリンクが壊れていないことを確認する。
        search_response = self.client.get(back_href)
        self.assertEqual(search_response.status_code, 200)
