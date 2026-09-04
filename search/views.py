from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from events.models import Tag
from events.services import EventService

from .criteria import SearchCriteria
from .models import SavedSearch
from .services import SavedSearchService, SearchService

SEARCH_SORT_FIELDS = {
    "start_asc": ("start_datetime", "pk"),
    "start_desc": ("-start_datetime", "pk"),
    "newest": ("-created_at", "pk"),
}


def _validation_message(error):
    return " ".join(error.messages)


def _parse_optional_int(value):
    #GET/POSTの文字列パラメータを任意のintへ変換する（未指定・不正値はNone）
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_optional_date(value):
    #GET/POSTの文字列パラメータ(ISO 8601)を任意のdateへ変換する（未指定・不正値はNone）
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_int_list(values):
    #タグIDのリストパラメータをintのリストへ変換する（不正値は無視する）
    result = []
    for value in values:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _parse_bool_flag(value):
    #チェックボックス等の明示的な真偽判定（"on"/"true"/"1"のみTrue）
    return value in ("on", "true", "1", "True", "yes")


def _build_criteria_from(params):
    #GET/POSTいずれのQueryDictからもSearchCriteriaを組み立てる共通処理
    return SearchCriteria(
        keyword=params.get("keyword", ""),
        location=params.get("location", ""),
        period_from=_parse_optional_date(params.get("period_from")),
        period_to=_parse_optional_date(params.get("period_to")),
        age_min=_parse_optional_int(params.get("age_min")),
        age_max=_parse_optional_int(params.get("age_max")),
        tag_ids=_parse_int_list(params.getlist("tag")),
    )


def _criteria_query_string(criteria, selected_sort="start_asc"):
    values = []
    if criteria.keyword:
        values.append(("keyword", criteria.keyword))
    if criteria.location:
        values.append(("location", criteria.location))
    if criteria.period_from:
        values.append(("period_from", criteria.period_from.isoformat()))
    if criteria.period_to:
        values.append(("period_to", criteria.period_to.isoformat()))
    values.extend(("tag", str(tag_id)) for tag_id in criteria.tag_ids)
    if selected_sort != "start_asc":
        values.append(("sort", selected_sort))
    return urlencode(values)


# --- 更新系ハンドラで使う「POSTに存在しなければ既存値を維持する」共通ヘルパー群。
# キーワード引数のたびに存在チェックを書くと漏れやすいため一本化している。


def _string_or_existing(params, key, existing):
    return params.get(key, existing)


def _date_or_existing(params, key, existing):
    if key not in params:
        return existing
    return _parse_optional_date(params.get(key))


def _int_or_existing(params, key, existing):
    if key not in params:
        return existing
    return _parse_optional_int(params.get(key))


def _bool_or_existing(params, key, existing):
    if key not in params:
        return existing
    return _parse_bool_flag(params.get(key))


def _tag_ids_or_existing(params, existing_ids):
    if "tag" not in params:
        return list(existing_ids)
    return _parse_int_list(params.getlist("tag"))


def _get_pk_or_bad_request(request):
    #POSTのpkパラメータをintへ検証する。不正な場合は400を返すためNoneではなく
    #HttpResponseBadRequestそのものを返す（呼び出し側で判定できるように）。
    pk = _parse_optional_int(request.POST.get("pk"))
    if pk is None:
        return None, HttpResponseBadRequest("pkが不正です。")
    return pk, None


def _handle_create(request):
    try:
        SavedSearchService.create(
            owner=request.user,
            keyword=request.POST.get("keyword", ""),
            location=request.POST.get("location", ""),
            period_from=_parse_optional_date(request.POST.get("period_from")),
            period_to=_parse_optional_date(request.POST.get("period_to")),
            age_min=_parse_optional_int(request.POST.get("age_min")),
            age_max=_parse_optional_int(request.POST.get("age_max")),
            # キー未送信時はモデルのdefault=Trueに合わせる（意図せずOFFにしない）
            notify_enabled=(
                True
                if "notify_enabled" not in request.POST
                else _parse_bool_flag(request.POST.get("notify_enabled"))
            ),
            tag_ids=_parse_int_list(request.POST.getlist("tag")),
        )
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    else:
        messages.success(request, "検索条件を保存しました。")
    return None


def _handle_update(request):
    pk, error_response = _get_pk_or_bad_request(request)
    if error_response is not None:
        return error_response

    # ownerで絞り込んで取得することで、他人のSavedSearchに対しては
    # 「存在するかどうか」自体を判別できない404にする(存在確認オラクル化を防ぐ)。
    saved_search = get_object_or_404(
        SavedSearch,
        pk=pk,
        owner=request.user,
        source=SavedSearch.Source.MANUAL,
    )

    try:
        SavedSearchService.update(
            saved_search=saved_search,
            user=request.user,
            keyword=_string_or_existing(request.POST, "keyword", saved_search.keyword),
            location=_string_or_existing(request.POST, "location", saved_search.location),
            period_from=_date_or_existing(request.POST, "period_from", saved_search.period_from),
            period_to=_date_or_existing(request.POST, "period_to", saved_search.period_to),
            age_min=_int_or_existing(request.POST, "age_min", saved_search.age_min),
            age_max=_int_or_existing(request.POST, "age_max", saved_search.age_max),
            notify_enabled=_bool_or_existing(
                request.POST, "notify_enabled", saved_search.notify_enabled
            ),
            tag_ids=_tag_ids_or_existing(
                request.POST, saved_search.tags.values_list("id", flat=True)
            ),
        )
    except ValidationError as error:
        messages.error(request, _validation_message(error))
    except PermissionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "保存した検索条件を更新しました。")
    return None


def _handle_delete(request):
    pk, error_response = _get_pk_or_bad_request(request)
    if error_response is not None:
        return error_response

    # updateと同様、owner絞り込みで他人のSavedSearchは404にする。
    saved_search = get_object_or_404(
        SavedSearch,
        pk=pk,
        owner=request.user,
        source=SavedSearch.Source.MANUAL,
    )

    try:
        SavedSearchService.delete(saved_search=saved_search, user=request.user)
    except PermissionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "保存した検索条件を削除しました。")
    return None


# POSTのactionパラメータとハンドラの対応表。create/update/delete以外は不正操作として扱う。
_POST_ACTIONS = {
    "create": _handle_create,
    "update": _handle_update,
    "delete": _handle_delete,
}


def search_results(request):
    #検索結果の表示(GET)と保存検索の作成・変更・削除(POST)を1つのURLで受ける。
    if request.method == "POST":
        # 保存検索の操作は本人のみ。検索結果の閲覧自体はログイン不要なのでGETは制限しない。
        if not request.user.is_authenticated:
            return HttpResponseForbidden("ログインが必要です。")

        handler = _POST_ACTIONS.get(request.POST.get("action"))
        if handler is None:
            return HttpResponseBadRequest("不正な操作です。")

        error_response = handler(request)
        if error_response is not None:
            return error_response

        # Post/Redirect/Getで二重送信を防ぎつつ、保存・更新した検索条件を画面に残す。
        query_string = _criteria_query_string(_build_criteria_from(request.POST))
        redirect_url = redirect("search:search_results").url
        if query_string:
            redirect_url = f"{redirect_url}?{query_string}"
        return redirect(redirect_url)

    criteria = _build_criteria_from(request.GET)
    selected_sort = request.GET.get("sort", "start_asc")
    if selected_sort not in SEARCH_SORT_FIELDS:
        selected_sort = "start_asc"

    events = EventService.with_rating_summary(
        SearchService.search(criteria)
        .select_related("organizer")
        .prefetch_related("tags")
    ).order_by(*SEARCH_SORT_FIELDS[selected_sort])

    saved_searches = []
    if request.user.is_authenticated:
        saved_searches = list(
            SavedSearch.objects.filter(
                owner=request.user,
                source=SavedSearch.Source.MANUAL,
            ).prefetch_related("tags")
        )
        for saved_search in saved_searches:
            saved_search.search_query = _criteria_query_string(
                SearchCriteria(
                    keyword=saved_search.keyword,
                    location=saved_search.location,
                    period_from=saved_search.period_from,
                    period_to=saved_search.period_to,
                    tag_ids=[tag.pk for tag in saved_search.tags.all()],
                )
            )

    context = {
        "events": events,
        "criteria": criteria,
        "saved_searches": saved_searches,
        "all_tags": Tag.objects.all(),
        "selected_sort": selected_sort,
        "search_query": _criteria_query_string(criteria, selected_sort),
    }
    return render(request, "search/search_results.html", context)
