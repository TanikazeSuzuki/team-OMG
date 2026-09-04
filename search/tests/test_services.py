from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from events.models import Event, Tag
from search.criteria import SearchCriteria
from search.models import SavedSearch
from search.services import MatchService, SavedSearchService, SearchService

User = get_user_model()


def _make_event(*, organizer, title="イベント", status=Event.Status.PUBLISH,
                 description="", location="", start_offset_days=1,
                 duration_days=1, min_age=None, max_age=None, tags=None):
    start = timezone.now() + timedelta(days=start_offset_days)
    end = start + timedelta(days=duration_days)
    event = Event.objects.create(
        title=title,
        description=description,
        organizer=organizer,
        start_datetime=start,
        end_datetime=end,
        location=location,
        min_age=min_age,
        max_age=max_age,
        status=status,
    )
    if tags:
        event.tags.set(tags)
    return event


class SearchServiceTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(email="organizer@example.com", password="pass12345")
        self.outdoor = Tag.objects.create(name="屋外")
        self.indoor = Tag.objects.create(name="屋内")

    def test_empty_criteria_returns_all_published_events(self):
        published = _make_event(organizer=self.organizer, title="公開イベント")
        _make_event(organizer=self.organizer, title="下書き", status=Event.Status.DRAFT)
        _make_event(organizer=self.organizer, title="中止", status=Event.Status.CANCEL)

        results = SearchService.search(SearchCriteria())

        self.assertIn(published, results)
        self.assertEqual(results.count(), 1)

    def test_draft_and_cancel_events_are_excluded(self):
        _make_event(organizer=self.organizer, title="下書き", status=Event.Status.DRAFT)
        _make_event(organizer=self.organizer, title="中止", status=Event.Status.CANCEL)

        results = SearchService.search(SearchCriteria(keyword=""))

        self.assertEqual(results.count(), 0)

    def test_keyword_matches_title_or_description(self):
        matching = _make_event(organizer=self.organizer, title="夏祭り", description="")
        _make_event(organizer=self.organizer, title="花火大会", description="夏祭りの様子")
        non_matching = _make_event(organizer=self.organizer, title="冬フェス", description="")

        results = SearchService.search(SearchCriteria(keyword="夏祭り"))

        self.assertIn(matching, results)
        self.assertNotIn(non_matching, results)
        self.assertEqual(results.count(), 2)

    def test_keyword_no_match_returns_empty(self):
        _make_event(organizer=self.organizer, title="夏祭り")

        results = SearchService.search(SearchCriteria(keyword="存在しないキーワード"))

        self.assertEqual(results.count(), 0)

    def test_location_filter(self):
        matching = _make_event(organizer=self.organizer, location="東京都渋谷区")
        non_matching = _make_event(organizer=self.organizer, location="大阪府大阪市")

        results = SearchService.search(SearchCriteria(location="東京"))

        self.assertIn(matching, results)
        self.assertNotIn(non_matching, results)

    def test_period_filter_overlapping_and_boundary(self):
        overlapping = _make_event(
            organizer=self.organizer, start_offset_days=5, duration_days=3
        )
        outside = _make_event(
            organizer=self.organizer, start_offset_days=100, duration_days=1
        )

        period_from = (timezone.now() + timedelta(days=4)).date()
        period_to = (timezone.now() + timedelta(days=10)).date()
        results = SearchService.search(
            SearchCriteria(period_from=period_from, period_to=period_to)
        )

        self.assertIn(overlapping, results)
        self.assertNotIn(outside, results)

    def test_tag_filter(self):
        matching = _make_event(organizer=self.organizer, tags=[self.outdoor])
        non_matching = _make_event(organizer=self.organizer, tags=[self.indoor])

        results = SearchService.search(SearchCriteria(tag_ids=[self.outdoor.id]))

        self.assertIn(matching, results)
        self.assertNotIn(non_matching, results)

    def test_tag_filter_does_not_duplicate_results(self):
        both_tags = Tag.objects.create(name="両方")
        event = _make_event(organizer=self.organizer, tags=[self.outdoor, both_tags])

        results = SearchService.search(
            SearchCriteria(tag_ids=[self.outdoor.id, both_tags.id])
        )

        self.assertEqual(list(results).count(event), 1)

    def test_combined_criteria_uses_and(self):
        matching = _make_event(
            organizer=self.organizer,
            title="夏祭り",
            location="東京都渋谷区",
            min_age=3,
            max_age=6,
        )
        wrong_location = _make_event(
            organizer=self.organizer,
            title="夏祭り",
            location="大阪府",
            min_age=3,
            max_age=6,
        )

        results = SearchService.search(
            SearchCriteria(keyword="夏祭り", location="東京")
        )

        self.assertIn(matching, results)
        self.assertNotIn(wrong_location, results)


class SavedSearchServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.other = User.objects.create_user(email="other@example.com", password="pass12345")
        self.tag = Tag.objects.create(name="屋外")

    def test_create_saved_search(self):
        saved_search = SavedSearchService.create(
            owner=self.owner, keyword="花火", tag_ids=[self.tag.id]
        )

        self.assertEqual(saved_search.owner, self.owner)
        self.assertIn(self.tag, saved_search.tags.all())

    def test_owner_can_update(self):
        saved_search = SavedSearchService.create(owner=self.owner, keyword="花火")

        updated = SavedSearchService.update(
            saved_search=saved_search, user=self.owner, keyword="夏祭り"
        )

        self.assertEqual(updated.keyword, "夏祭り")

    def test_non_owner_cannot_update(self):
        saved_search = SavedSearchService.create(owner=self.owner, keyword="花火")

        with self.assertRaises(PermissionError):
            SavedSearchService.update(
                saved_search=saved_search, user=self.other, keyword="夏祭り"
            )

    def test_owner_can_delete(self):
        saved_search = SavedSearchService.create(owner=self.owner, keyword="花火")

        SavedSearchService.delete(saved_search=saved_search, user=self.owner)

        self.assertFalse(SavedSearch.objects.filter(pk=saved_search.pk).exists())

    def test_non_owner_cannot_delete(self):
        saved_search = SavedSearchService.create(owner=self.owner, keyword="花火")

        with self.assertRaises(PermissionError):
            SavedSearchService.delete(saved_search=saved_search, user=self.other)


class MatchServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="pass12345")
        self.tag = Tag.objects.create(name="屋外")
        self.other_tag = Tag.objects.create(name="屋内")

    def test_matches_when_all_criteria_align(self):
        event = _make_event(
            organizer=self.owner,
            title="夏祭り",
            location="東京都渋谷区",
            min_age=3,
            max_age=6,
            tags=[self.tag],
        )
        saved_search = SavedSearchService.create(
            owner=self.owner,
            keyword="夏祭り",
            location="東京",
            tag_ids=[self.tag.id],
        )

        self.assertTrue(MatchService.matches(saved_search, event))

    def test_does_not_match_when_keyword_missing(self):
        event = _make_event(organizer=self.owner, title="冬フェス")
        saved_search = SavedSearchService.create(owner=self.owner, keyword="夏祭り")

        self.assertFalse(MatchService.matches(saved_search, event))

    def test_does_not_match_draft_or_cancelled_events(self):
        draft_event = _make_event(
            organizer=self.owner, status=Event.Status.DRAFT
        )
        saved_search = SavedSearchService.create(owner=self.owner)

        self.assertFalse(MatchService.matches(saved_search, draft_event))

    def test_does_not_match_when_tags_disjoint(self):
        event = _make_event(organizer=self.owner, tags=[self.other_tag])
        saved_search = SavedSearchService.create(
            owner=self.owner, tag_ids=[self.tag.id]
        )

        self.assertFalse(MatchService.matches(saved_search, event))

    def test_search_service_and_match_service_agree(self):
        """SearchServiceの絞り込み結果とMatchServiceの一致判定が食い違わないことを保証する。"""
        matching_event = _make_event(
            organizer=self.owner,
            title="夏祭り",
            location="東京都渋谷区",
            min_age=3,
            max_age=6,
            tags=[self.tag],
        )
        non_matching_event = _make_event(
            organizer=self.owner,
            title="冬フェス",
            location="大阪府",
            min_age=20,
            max_age=30,
            tags=[self.other_tag],
        )
        saved_search = SavedSearchService.create(
            owner=self.owner,
            keyword="夏祭り",
            location="東京",
            tag_ids=[self.tag.id],
        )
        criteria = SearchCriteria(
            keyword=saved_search.keyword,
            location=saved_search.location,
            period_from=saved_search.period_from,
            period_to=saved_search.period_to,
            tag_ids=list(saved_search.tags.values_list("id", flat=True)),
        )
        search_results = SearchService.search(criteria)

        for event in (matching_event, non_matching_event):
            self.assertEqual(
                event in search_results,
                MatchService.matches(saved_search, event),
                msg=f"event={event.title} でSearchServiceとMatchServiceの判定が食い違っています。",
            )

    def test_search_service_and_match_service_agree_on_jst_date_boundary(self):
        """タイムゾーン境界（JST 00:00〜09:00 = UTC前日）でも両者の判定が一致することを保証する。

        SearchServiceの`__date`ルックアップはAsia/Tokyoへ変換してから日付を
        取り出す一方、DBから読み出したdatetimeはUTC基準になる（USE_TZ=True）。
        MatchServiceが素の.date()を使うとJST 00:00〜09:00の開始イベントで
        UTC日付とズレるため、この境界を固定日時で明示的に検証する。
        """
        jst = timezone.get_current_timezone()
        start = timezone.make_aware(datetime(2026, 1, 10, 6, 0), jst)  # JST 06:00
        end = start + timedelta(hours=2)
        event = Event.objects.create(
            title="早朝イベント",
            organizer=self.owner,
            start_datetime=start,
            end_datetime=end,
            status=Event.Status.PUBLISH,
        )
        # DB往復後のdatetimeで検証する。SQLite+USE_TZ=Trueでは読み出し時に
        # UTC基準のaware datetimeになるため、生成直後のインメモリオブジェクト
        # （構築時のtzinfoをそのまま保持）では境界バグを再現できない。
        event.refresh_from_db()

        saved_search = SavedSearchService.create(
            owner=self.owner,
            period_from=date(2026, 1, 10),
            period_to=date(2026, 1, 10),
        )
        criteria = SearchCriteria(
            period_from=saved_search.period_from, period_to=saved_search.period_to
        )

        search_results = SearchService.search(criteria)

        self.assertIn(event, search_results)
        self.assertTrue(MatchService.matches(saved_search, event))
        self.assertEqual(event in search_results, MatchService.matches(saved_search, event))
