import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event, Tag
from interactions.models import EventView, Favorite, Like, Rating


User = get_user_model()


class ParticipantUiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organizer = User.objects.create_user(
            email="organizer@example.com",
            password="test-pass-123",
            name="主催者",
            role=User.Role.ORGANIZER,
        )
        cls.participant = User.objects.create_user(
            email="participant@example.com",
            password="test-pass-123",
            name="参加者",
        )
        cls.other_user = User.objects.create_user(
            email="other@example.com",
            password="test-pass-123",
            name="別の参加者",
        )
        cls.tag = Tag.objects.create(name="親子")
        now = timezone.now()

        cls.upcoming_event = Event.objects.create(
            title="親子で楽しむ工作教室",
            description="木を使っておもちゃを作ります。",
            organizer=cls.organizer,
            start_datetime=now + timedelta(days=2),
            end_datetime=now + timedelta(days=2, hours=2),
            location="大阪市",
            min_age=5,
            max_age=12,
            status=Event.Status.PUBLISH,
        )
        cls.upcoming_event.tags.add(cls.tag)
        cls.finished_event = Event.objects.create(
            title="終了した音楽イベント",
            description="評価確認用のイベントです。",
            organizer=cls.organizer,
            start_datetime=now - timedelta(days=2),
            end_datetime=now - timedelta(days=1),
            location="京都市",
            status=Event.Status.PUBLISH,
        )
        cls.draft_event = Event.objects.create(
            title="非公開イベント",
            organizer=cls.organizer,
            start_datetime=now + timedelta(days=3),
            end_datetime=now + timedelta(days=3, hours=2),
            status=Event.Status.DRAFT,
        )

    def test_home_shows_only_upcoming_published_events(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EventMatch")
        self.assertNotContains(response, "EventMatchTechjamsummer")
        self.assertNotContains(response, "TechJamSummer")
        self.assertContains(response, self.upcoming_event.title)
        self.assertNotContains(response, self.finished_event.title)
        self.assertNotContains(response, self.draft_event.title)
        self.assertContains(response, reverse("search:search_results"))

    def test_authenticated_header_has_settings_button_and_footer_has_no_home_link(self):
        self.client.force_login(self.participant)

        response = self.client.get(reverse("core:home"))
        html = response.content.decode()

        self.assertContains(response, reverse("accounts:preferences"), count=1)
        self.assertContains(response, 'class="settings-button"')
        self.assertContains(response, 'aria-label="設定"')
        self.assertContains(response, "/static/images/settings-gear.jpg")
        # ホームへのリンクはヘッダーのロゴとメニューだけで、フッターには置かない。
        self.assertEqual(html.count('href="/"'), 2)

    def test_event_detail_records_authenticated_view(self):
        self.client.force_login(self.participant)

        response = self.client.get(
            reverse("events:event_detail", args=[self.upcoming_event.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "events/event_detail.html")
        self.assertTrue(
            EventView.objects.filter(
                event=self.upcoming_event,
                user=self.participant,
            ).exists()
        )
        self.assertContains(response, "評価・レビューはイベント終了後に投稿できます")

    def test_draft_event_detail_returns_not_found(self):
        response = self.client.get(
            reverse("events:event_detail", args=[self.draft_event.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_favorite_and_like_can_be_toggled_from_detail(self):
        self.client.force_login(self.participant)
        favorite_url = reverse(
            "interactions:toggle_favorite", args=[self.upcoming_event.pk]
        )
        like_url = reverse("interactions:toggle_like", args=[self.upcoming_event.pk])

        self.client.post(favorite_url)
        self.client.post(like_url)
        self.assertTrue(
            Favorite.objects.filter(
                event=self.upcoming_event,
                user=self.participant,
            ).exists()
        )
        self.assertTrue(
            Like.objects.filter(
                event=self.upcoming_event,
                user=self.participant,
            ).exists()
        )

        self.client.post(favorite_url)
        self.client.post(like_url)
        self.assertFalse(
            Favorite.objects.filter(
                event=self.upcoming_event,
                user=self.participant,
            ).exists()
        )
        self.assertFalse(
            Like.objects.filter(
                event=self.upcoming_event,
                user=self.participant,
            ).exists()
        )

    def test_rating_zero_can_be_created_updated_and_deleted(self):
        self.client.force_login(self.participant)
        create_url = reverse(
            "interactions:submit_review", args=[self.finished_event.pk]
        )

        response = self.client.post(
            create_url,
            {"rating": "0", "comment": "今回は評価なし"},
        )
        self.assertRedirects(
            response,
            reverse("events:event_detail", args=[self.finished_event.pk]),
        )
        rating = Rating.objects.get(
            event=self.finished_event,
            user=self.participant,
        )
        self.assertEqual(rating.rating, 0)

        update_url = reverse(
            "interactions:update_rating",
            args=[self.finished_event.pk, rating.pk],
        )
        self.client.post(update_url, {"rating": "5", "comment": "とても良かった"})
        rating.refresh_from_db()
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.comment, "とても良かった")

        delete_url = reverse(
            "interactions:delete_rating",
            args=[self.finished_event.pk, rating.pk],
        )
        self.client.post(delete_url)
        self.assertFalse(Rating.objects.filter(pk=rating.pk).exists())

    def test_upcoming_event_rating_error_is_displayed(self):
        self.client.force_login(self.participant)

        response = self.client.post(
            reverse("interactions:submit_review", args=[self.upcoming_event.pk]),
            {"rating": "5", "comment": "開催前"},
            follow=True,
        )

        self.assertContains(response, "イベント終了後にのみ評価・レビューを投稿できます")
        self.assertFalse(
            Rating.objects.filter(
                event=self.upcoming_event,
                user=self.participant,
            ).exists()
        )

    def test_favorites_page_hides_non_published_events(self):
        Favorite.objects.create(event=self.upcoming_event, user=self.participant)
        Favorite.objects.create(event=self.draft_event, user=self.participant)
        self.client.force_login(self.participant)

        response = self.client.get(reverse("events:my_favorites"))

        self.assertContains(response, self.upcoming_event.title)
        self.assertNotContains(response, self.draft_event.title)

    def test_search_filters_and_sorts_results(self):
        response = self.client.get(
            reverse("search:search_results"),
            {"keyword": "イベント", "sort": "start_desc"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "search/search_results.html")
        self.assertContains(response, self.finished_event.title)
        self.assertNotContains(response, self.upcoming_event.title)
        self.assertNotContains(response, self.draft_event.title)
        self.assertEqual(response.context["selected_sort"], "start_desc")

    def test_other_users_rating_is_listed_with_zero_score(self):
        Rating.objects.create(
            event=self.finished_event,
            user=self.other_user,
            rating=0,
            comment="コメント",
        )

        response = self.client.get(
            reverse("events:event_detail", args=[self.finished_event.pk])
        )

        self.assertContains(response, "評価 0 / 5")
        self.assertContains(response, "コメント")


def _extract_card_detail_url(html, pk):
    match = re.search(r'href="(/events/%d/\?next=[^"]+)"' % pk, html)
    return match.group(1) if match else None


def _extract_back_link_href(html):
    match = re.search(r'class="back-link" href="([^"]+)"', html)
    if match is None:
        return None
    # テンプレートのautoescapeにより '&' が '&amp;' としてレンダリングされるため、
    # 実際のURLとして再利用するために戻す。
    return match.group(1).replace("&amp;", "&")


class BackNavigationTests(TestCase):
    #サイト全体がログイン必須(LoginRequiredMiddleware)のため、各GETはログイン状態で行う。
    @classmethod
    def setUpTestData(cls):
        cls.organizer = User.objects.create_user(
            email="backnav-organizer@example.com",
            password="test-pass-123",
            name="主催者",
            role=User.Role.ORGANIZER,
        )
        cls.participant = User.objects.create_user(
            email="backnav-participant@example.com",
            password="test-pass-123",
            name="参加者",
        )
        now = timezone.now()
        cls.event = Event.objects.create(
            title="戻り導線確認イベント",
            description="戻る導線のテスト用イベントです。",
            organizer=cls.organizer,
            start_datetime=now + timedelta(days=2),
            end_datetime=now + timedelta(days=2, hours=2),
            location="東京都",
            status=Event.Status.PUBLISH,
        )

    def setUp(self):
        self.client.force_login(self.participant)

    def test_back_link_from_home_targets_home_with_correct_label(self):
        home_response = self.client.get(reverse("core:home"))
        detail_url = _extract_card_detail_url(
            home_response.content.decode(), self.event.pk
        )
        self.assertIsNotNone(
            detail_url, "ホームのイベントカードにnext付きリンクが見つかりません"
        )

        detail_response = self.client.get(detail_url)

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.context["next_url"], reverse("core:home"))
        self.assertEqual(detail_response.context["back_label"], "ホームへ戻る")
        self.assertContains(detail_response, "← ホームへ戻る")

        back_href = _extract_back_link_href(detail_response.content.decode())
        self.assertEqual(back_href, reverse("core:home"))

        final_response = self.client.get(back_href)
        self.assertEqual(final_response.status_code, 200)
        self.assertContains(final_response, self.event.title)

    def test_event_detail_without_next_falls_back_to_home(self):
        response = self.client.get(
            reverse("events:event_detail", args=[self.event.pk])
        )

        self.assertEqual(response.context["next_url"], reverse("core:home"))
        self.assertEqual(response.context["back_label"], "ホームへ戻る")
        self.assertContains(response, "← ホームへ戻る")

    def test_event_detail_rejects_absolute_url_next_and_falls_back(self):
        response = self.client.get(
            reverse("events:event_detail", args=[self.event.pk]),
            {"next": "https://evil.example.com/"},
        )

        self.assertNotContains(response, "evil.example.com")
        self.assertEqual(response.context["next_url"], reverse("core:home"))
        self.assertEqual(response.context["back_label"], "ホームへ戻る")

    def test_event_detail_rejects_protocol_relative_next_and_falls_back(self):
        response = self.client.get(
            reverse("events:event_detail", args=[self.event.pk]),
            {"next": "//evil.example.com"},
        )

        self.assertNotContains(response, "evil.example.com")
        self.assertEqual(response.context["next_url"], reverse("core:home"))
        self.assertEqual(response.context["back_label"], "ホームへ戻る")
