from django.db.models import Q
from django.utils import timezone

from .logic import age_ranges_overlap, is_criteria_empty, period_overlaps
from .models import SavedSearch
from .queries import published_events


class SearchService:
    #検索条件で公開イベントを絞り込むサービス。異なる種類の条件は原則AND結合する。
    @staticmethod
    def search(criteria):
        queryset = published_events()

        if is_criteria_empty(criteria):
            return queryset.distinct()

        if criteria.keyword:
            queryset = queryset.filter(
                Q(title__icontains=criteria.keyword)
                | Q(description__icontains=criteria.keyword)
            )

        if criteria.location:
            queryset = queryset.filter(location__icontains=criteria.location)

        # 期間の重なり判定（logic.period_overlapsと同じ境界解釈に揃える）
        if criteria.period_from is not None:
            queryset = queryset.filter(end_datetime__date__gte=criteria.period_from)

        if criteria.period_to is not None:
            queryset = queryset.filter(start_datetime__date__lte=criteria.period_to)

        # 対象年齢の入力欄は画面上では非表示だが、既存データとの互換性のため
        # 内部の検索条件としては引き続き扱う。
        if criteria.age_min is not None:
            queryset = queryset.filter(
                Q(max_age__isnull=True) | Q(max_age__gte=criteria.age_min)
            )

        if criteria.age_max is not None:
            queryset = queryset.filter(
                Q(min_age__isnull=True) | Q(min_age__lte=criteria.age_max)
            )

        # 複数タグはOR条件。選択したタグを1つでも持つイベントを残す。
        tag_ids = list(criteria.tag_ids)
        if tag_ids:
            queryset = queryset.filter(tags__in=tag_ids)

        return queryset.distinct()


class SavedSearchService:
    #保存検索の作成・変更・削除を行うサービス。所有者本人だけが変更・削除できる。
    @staticmethod
    def create(*, owner, tag_ids=None, **fields):
        saved_search = SavedSearch(owner=owner, **fields)
        saved_search.full_clean()
        saved_search.save()
        if tag_ids is not None:
            saved_search.tags.set(tag_ids)
        return saved_search

    @staticmethod
    def update(*, saved_search, user, tag_ids=None, **fields):
        if user != saved_search.owner:
            raise PermissionError("この保存検索を編集する権限がありません。")

        for field_name, value in fields.items():
            setattr(saved_search, field_name, value)

        saved_search.full_clean()
        saved_search.save()

        if tag_ids is not None:
            saved_search.tags.set(tag_ids)

        return saved_search

    @staticmethod
    def delete(*, saved_search, user):
        if user != saved_search.owner:
            raise PermissionError("この保存検索を削除する権限がありません。")
        saved_search.delete()

    @staticmethod
    def get_notification_preference(*, owner):
        return (
            SavedSearch.objects.filter(
                owner=owner,
                source=SavedSearch.Source.PREFERENCE,
            )
            .prefetch_related("tags")
            .first()
        )

    @staticmethod
    def sync_notification_preference(
        *, owner, location, tag_ids=None, notify_enabled=True
    ):
        """設定画面の開催地・タグを通知専用の保存条件へ同期する。"""
        location = (location or "").strip()
        tag_ids = list(tag_ids or [])
        saved_search = SavedSearchService.get_notification_preference(owner=owner)

        # 条件が空なら全イベント通知にはせず、専用条件自体を削除する。
        if not location and not tag_ids:
            if saved_search is not None:
                saved_search.delete()
            return None

        if saved_search is None:
            saved_search = SavedSearch(
                owner=owner,
                source=SavedSearch.Source.PREFERENCE,
            )

        saved_search.keyword = ""
        saved_search.location = location
        saved_search.period_from = None
        saved_search.period_to = None
        saved_search.age_min = None
        saved_search.age_max = None
        saved_search.priority = ""
        saved_search.notify_enabled = notify_enabled
        saved_search.full_clean()
        saved_search.save()
        saved_search.tags.set(tag_ids)
        return saved_search


class MatchService:
    #保存検索とイベントが一致するかどうかを判定するサービス。
    #SearchServiceのSQLフィルタと同じ判定基準になるよう、logic.pyの関数を共有する。
    @staticmethod
    def matches(saved_search, event):
        if event.status in (event.Status.DRAFT, event.Status.CANCEL):
            return False

        if saved_search.keyword:
            keyword = saved_search.keyword.lower()
            if keyword not in event.title.lower() and keyword not in event.description.lower():
                return False

        if saved_search.location:
            if saved_search.location.lower() not in event.location.lower():
                return False

        # SearchServiceの`__date`ルックアップは現在のタイムゾーン(Asia/Tokyo)に
        # 変換してから日付を取り出すため、ここでも同じくlocaltimeで揃える。
        # （USE_TZ=True環境ではDBから取得した日時はUTC基準になるため、素の
        # .date()を使うと日付境界付近でSearchServiceと判定がずれる）
        if not period_overlaps(
            saved_search.period_from,
            saved_search.period_to,
            timezone.localtime(event.start_datetime).date(),
            timezone.localtime(event.end_datetime).date(),
        ):
            return False

        if not age_ranges_overlap(
            saved_search.age_min, saved_search.age_max, event.min_age, event.max_age
        ):
            return False

        # .all()でイテレートしてIDを集める（.values_list()は related manager の
        # prefetch_relatedキャッシュを使わず毎回クエリを発行してしまうため、
        # 呼び出し側でprefetch_related済みのsaved_search/eventを渡された場合に
        # そのキャッシュを活かせるよう.all()を使っている。未prefetchの場合は
        # 従来通り1回ずつクエリが発行されるだけで、結果は同じ）
        tag_ids = {tag.id for tag in saved_search.tags.all()}
        if tag_ids:
            event_tag_ids = {tag.id for tag in event.tags.all()}
            if not (tag_ids & event_tag_ids):
                return False

        return True
