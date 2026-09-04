import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from search.models import SavedSearch
from search.services import SavedSearchService

User = get_user_model()


class AgeSearchHiddenTests(TestCase):
    def setUp(self):
        self.url = reverse("search:search_results")

    def test_search_page_has_no_age_inputs(self):
        response = self.client.get(self.url)

        self.assertNotContains(response, 'name="age_min"')
        self.assertNotContains(response, 'name="age_max"')
        self.assertNotContains(response, "対象年齢の下限")
        self.assertNotContains(response, "対象年齢の上限")

class SearchResultsPostDispatchTests(TestCase):
    #POST側の共通ディスパッチ(認証・action判定)の振る舞いを検証する。
    def setUp(self):
        self.url = reverse("search:search_results")
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")

    def test_anonymous_post_is_forbidden(self):
        response = self.client.post(self.url, {"action": "create", "keyword": "花火"})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SavedSearch.objects.exists())

    def test_unknown_action_is_bad_request(self):
        self.client.force_login(self.owner)

        response = self.client.post(self.url, {"action": "bogus"})

        self.assertEqual(response.status_code, 400)

    def test_missing_action_is_bad_request(self):
        self.client.force_login(self.owner)

        response = self.client.post(self.url, {"keyword": "花火"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SavedSearch.objects.exists())


class SavedSearchOwnershipTests(TestCase):
    #他人のSavedSearchに対するupdate/deleteが404になり、実データも変更されないことを検証する。
    def setUp(self):
        self.url = reverse("search:search_results")
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.other = User.objects.create_user(email="other@example.com", password="pass12345")
        self.saved_search = SavedSearch.objects.create(
            owner=self.owner, keyword="花火", location="東京"
        )

    def test_update_others_saved_search_returns_404_and_does_not_change_data(self):
        self.client.force_login(self.other)

        response = self.client.post(
            self.url,
            {"action": "update", "pk": self.saved_search.pk, "keyword": "乗っ取り"},
        )

        self.assertEqual(response.status_code, 404)
        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.keyword, "花火")

    def test_delete_others_saved_search_returns_404_and_does_not_delete(self):
        self.client.force_login(self.other)

        response = self.client.post(
            self.url, {"action": "delete", "pk": self.saved_search.pk}
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(SavedSearch.objects.filter(pk=self.saved_search.pk).exists())

    def test_owner_can_update_own_saved_search(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {"action": "update", "pk": self.saved_search.pk, "keyword": "夏祭り"},
        )

        self.assertEqual(response.status_code, 302)
        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.keyword, "夏祭り")

    def test_owner_can_delete_own_saved_search(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url, {"action": "delete", "pk": self.saved_search.pk}
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SavedSearch.objects.filter(pk=self.saved_search.pk).exists())


class SavedSearchInvalidPkTests(TestCase):
    #非数値のpkが渡された場合に500にならず400を返すことを検証する(修正2の回帰テスト)。
    def setUp(self):
        self.url = reverse("search:search_results")
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.client.force_login(self.owner)

    def test_update_with_non_numeric_pk_is_bad_request(self):
        response = self.client.post(
            self.url, {"action": "update", "pk": "abc", "keyword": "花火"}
        )

        self.assertEqual(response.status_code, 400)

    def test_delete_with_non_numeric_pk_is_bad_request(self):
        response = self.client.post(self.url, {"action": "delete", "pk": "abc"})

        self.assertEqual(response.status_code, 400)

    def test_update_with_missing_pk_is_bad_request(self):
        response = self.client.post(
            self.url, {"action": "update", "keyword": "花火"}
        )

        self.assertEqual(response.status_code, 400)


class SavedSearchPartialUpdateTests(TestCase):
    #未送信フィールドが既存値を消してしまわないことを検証する(修正1の回帰テスト)。
    def setUp(self):
        self.url = reverse("search:search_results")
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.client.force_login(self.owner)
        self.saved_search = SavedSearch.objects.create(
            owner=self.owner,
            keyword="花火",
            location="東京",
            period_from="2026-01-01",
            period_to="2026-01-31",
            age_min=3,
            age_max=10,
        )

    def test_updating_only_keyword_keeps_other_fields(self):
        response = self.client.post(
            self.url,
            {"action": "update", "pk": self.saved_search.pk, "keyword": "夏祭り"},
        )

        self.assertEqual(response.status_code, 302)
        self.saved_search.refresh_from_db()
        self.assertEqual(self.saved_search.keyword, "夏祭り")
        self.assertEqual(self.saved_search.location, "東京")
        self.assertEqual(str(self.saved_search.period_from), "2026-01-01")
        self.assertEqual(str(self.saved_search.period_to), "2026-01-31")
        self.assertEqual(self.saved_search.age_min, 3)
        self.assertEqual(self.saved_search.age_max, 10)

    def test_explicitly_clearing_a_field_with_empty_string_still_works(self):
        #period_fromキー自体は送信し、値を空にした場合は明示的なクリアとして扱われる
        response = self.client.post(
            self.url,
            {
                "action": "update",
                "pk": self.saved_search.pk,
                "period_from": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.saved_search.refresh_from_db()
        self.assertIsNone(self.saved_search.period_from)
        # period_toは未送信のため維持される
        self.assertEqual(str(self.saved_search.period_to), "2026-01-31")


class SavedSearchNotifyEnabledDefaultTests(TestCase):
    #notify_enabledを送信しないcreateでモデルのdefault=Trueが維持されることを検証する(修正4の回帰テスト)。
    def setUp(self):
        self.url = reverse("search:search_results")
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.client.force_login(self.owner)

    def test_create_without_notify_enabled_defaults_to_true(self):
        response = self.client.post(self.url, {"action": "create", "keyword": "花火"})

        self.assertEqual(response.status_code, 302)
        saved_search = SavedSearch.objects.get(owner=self.owner, keyword="花火")
        self.assertTrue(saved_search.notify_enabled)

    def test_create_with_notify_enabled_off_value_is_false(self):
        response = self.client.post(
            self.url,
            {"action": "create", "keyword": "夏祭り", "notify_enabled": "false"},
        )

        self.assertEqual(response.status_code, 302)
        saved_search = SavedSearch.objects.get(owner=self.owner, keyword="夏祭り")
        self.assertFalse(saved_search.notify_enabled)

    def test_create_with_notify_enabled_on_value_is_true(self):
        response = self.client.post(
            self.url,
            {"action": "create", "keyword": "花見", "notify_enabled": "on"},
        )

        self.assertEqual(response.status_code, 302)
        saved_search = SavedSearch.objects.get(owner=self.owner, keyword="花見")
        self.assertTrue(saved_search.notify_enabled)

    def test_update_without_notify_enabled_keeps_existing_value(self):
        saved_search = SavedSearch.objects.create(
            owner=self.owner, keyword="花火", notify_enabled=False
        )

        response = self.client.post(
            self.url,
            {"action": "update", "pk": saved_search.pk, "keyword": "花火2"},
        )

        self.assertEqual(response.status_code, 302)
        saved_search.refresh_from_db()
        self.assertFalse(saved_search.notify_enabled)


class PreferenceSavedSearchVisibilityTests(TestCase):
    def test_search_page_does_not_show_settings_generated_condition(self):
        owner = User.objects.create_user(
            email="hidden-preference@example.com", password="pass12345"
        )
        manual = SavedSearch.objects.create(owner=owner, keyword="花火")
        preference = SavedSearchService.sync_notification_preference(
            owner=owner,
            location="東京都",
            notify_enabled=True,
        )
        self.client.force_login(owner)

        response = self.client.get(reverse("search:search_results"))

        self.assertQuerySetEqual(
            response.context["saved_searches"],
            [manual],
        )
        self.assertNotContains(response, f'name="pk" value="{preference.pk}"')

    def test_search_page_cannot_update_settings_generated_condition(self):
        owner = User.objects.create_user(
            email="protected-preference@example.com", password="pass12345"
        )
        preference = SavedSearchService.sync_notification_preference(
            owner=owner,
            location="東京都",
            notify_enabled=True,
        )
        self.client.force_login(owner)

        response = self.client.post(
            reverse("search:search_results"),
            {
                "action": "update",
                "pk": preference.pk,
                "location": "大阪府",
            },
        )

        self.assertEqual(response.status_code, 404)
        preference.refresh_from_db()
        self.assertEqual(preference.location, "東京都")


class SearchBackNavigationRoundTripTests(TestCase):
    #検索結果 -> 詳細 -> 戻るリンクを実際にたどり、同じ検索結果に戻れることを検証する。
    #サイト全体がログイン必須(LoginRequiredMiddleware)のため、ログイン状態でGETする。
    @classmethod
    def setUpTestData(cls):
        cls.organizer = User.objects.create_user(
            email="search-backnav-organizer@example.com", password="pass12345"
        )
        cls.viewer = User.objects.create_user(
            email="search-backnav-viewer@example.com", password="pass12345"
        )
        now = timezone.now()
        cls.matching_event = Event.objects.create(
            title="親子 イベント 夏祭り",
            organizer=cls.organizer,
            start_datetime=now + timedelta(days=1),
            end_datetime=now + timedelta(days=1, hours=2),
            location="大阪市",
            status=Event.Status.PUBLISH,
        )
        cls.other_event = Event.objects.create(
            title="スポーツ大会",
            organizer=cls.organizer,
            start_datetime=now + timedelta(days=2),
            end_datetime=now + timedelta(days=2, hours=2),
            location="東京都",
            status=Event.Status.PUBLISH,
        )

    def setUp(self):
        self.client.force_login(self.viewer)

    def test_following_back_link_returns_to_same_search_results(self):
        # 非ASCII + スペース + 2パラメータ以上のクエリでエンコードの往復を検証する。
        query_params = {"keyword": "親子 イベント", "sort": "newest"}

        search_response = self.client.get(
            reverse("search:search_results"), query_params
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertContains(search_response, self.matching_event.title)
        self.assertNotContains(search_response, self.other_event.title)

        html = search_response.content.decode()
        match = re.search(
            r'href="(/events/%d/\?next=[^"]+)"' % self.matching_event.pk, html
        )
        self.assertIsNotNone(
            match, "検索結果のイベントカードにnext付きリンクが見つかりません"
        )
        detail_url = match.group(1)

        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "← 検索結果へ戻る")

        back_match = re.search(
            r'class="back-link" href="([^"]+)"', detail_response.content.decode()
        )
        self.assertIsNotNone(back_match)
        back_href = back_match.group(1).replace("&amp;", "&")

        followed_response = self.client.get(back_href)

        self.assertEqual(followed_response.status_code, 200)
        # 文字列一致だけで終わらせず、実際に返ってきた結果集合・contextが
        # 元の検索結果と一致することを確認する。
        self.assertEqual(
            list(followed_response.context["events"]),
            list(search_response.context["events"]),
        )
        self.assertEqual(
            followed_response.context["criteria"].keyword,
            search_response.context["criteria"].keyword,
        )
        self.assertEqual(
            followed_response.context["selected_sort"],
            search_response.context["selected_sort"],
        )
        self.assertContains(followed_response, self.matching_event.title)
        self.assertNotContains(followed_response, self.other_event.title)
