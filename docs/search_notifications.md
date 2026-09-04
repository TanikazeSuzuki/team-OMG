# search / notifications アプリ 利用ガイド

対象: `search`アプリ・`notifications`アプリ(検索・保存条件・マッチング・通知機能)。
他アプリ担当者、および将来の自分向けのリファレンス。

実装の正確な仕様は本ドキュメントの記述時点のソースコードを直接読んで記載している
(`search/`・`notifications/`配下、`config/settings.py`・`config/urls.py`)。

## 1. 概要

`search`/`notifications`アプリは、以下の一連の機能を提供する。

- **公開イベント検索**: キーワード・場所・開催期間・対象年齢・タグで、公開中(下書き・
  中止を除く)のイベントを絞り込む。
- **保存検索(SavedSearch)のCRUD**: ログインユーザーが検索条件を保存し、後から
  編集・削除できる。
- **一致判定(マッチング)**: 保存検索とイベントが条件的に一致するかどうかを判定する。
- **一致通知(Notification)**: `notify_enabled=True`の保存検索が公開イベントと一致した
  場合に通知を作成し、通知の一覧表示・既読化を提供する。

検索・保存検索のURLは`/search/`を単一のエンドポイントとして採用しており、
GET(検索結果表示)とPOST(`action=create`/`update`/`delete`による保存検索の
CRUD)を同一URL・同一ビューで受け付ける(詳細はセクション2参照)。

## 2. URL一覧

### 2.1 `/search/`(`search`アプリ、`app_name="search"`)

`search/urls.py`は以下の1パターンのみ:

```python
urlpatterns = [
    path("", views.search_results, name="search_results"),
]
```

`config/urls.py`側で`path("search/", include("search.urls", namespace="search"))`
としてマウントされているため、実際のURLは`/search/`のみ。GET(検索結果表示)と
POST(保存検索のCRUD)を同一URL・同一ビュー(`search_results`)で処理する。

#### GET `/search/`(検索)

ログイン不要。クエリパラメータはすべて任意(未指定または空は「条件なし」)。

| パラメータ | 型 | 意味 |
|---|---|---|
| `keyword` | 文字列 | イベントの`title`または`description`に部分一致(大小無視) |
| `location` | 文字列 | イベントの`location`に部分一致(大小無視) |
| `period_from` | 日付(`YYYY-MM-DD`) | 開催期間の下限。不正な形式は無視されNone扱い |
| `period_to` | 日付(`YYYY-MM-DD`) | 開催期間の上限。不正な形式は無視されNone扱い |
| `age_min` | 整数 | 対象年齢の下限。画面上では非表示だが内部互換性のため利用可能 |
| `age_max` | 整数 | 対象年齢の上限。画面上では非表示だが内部互換性のため利用可能 |
| `tag` | 整数(複数指定可) | タグID。複数指定時はOR(いずれかのタグを持つイベント) |

レスポンスのcontext: `events`(検索結果のQuerySet)、`criteria`(組み立てられた
`SearchCriteria`)、`saved_searches`(ログイン時のみ本人の保存検索一覧、未ログイン時は
空QuerySet)、`all_tags`(タグ選択肢用の全`Tag`一覧)。テンプレートは
`search/templates/search/search_results.html`。

#### POST `/search/`(保存検索のCRUD)

**ログイン必須**(未認証の場合`403 Forbidden`を返す。GET側はログイン不要のため、
ログイン判定はPOST分岐の先頭でのみ行っている)。`action`パラメータで処理を分岐する。

| パラメータ | 必須/任意 | 意味 |
|---|---|---|
| `action` | **必須** | `"create"` / `"update"` / `"delete"` のいずれか。それ以外・未指定は`400 Bad Request` |
| `pk` | `update`/`delete`時**必須** | 対象`SavedSearch`のID。非数値・未送信は`400 Bad Request`。本人以外が所有するIDを指定した場合は`404 Not Found`(所有者で絞り込んだクエリで取得するため、他人のデータの存在有無自体を判別できない) |
| `keyword` | 任意 | `create`: 省略時は空文字。`update`: **キー自体が無ければ既存値を維持**、キーがあれば(空文字でも)その値で上書き |
| `location` | 任意 | `keyword`と同様 |
| `period_from` | 任意 | `create`: 省略時はNone。`update`: キー自体が無ければ既存値維持、キーがあれば(空文字でも)パース結果(不正・空文字はNone)で上書き |
| `period_to` | 任意 | `period_from`と同様 |
| `age_min` | 任意 | 画面上では非表示。送信された場合は対象年齢の下限として保持 |
| `age_max` | 任意 | 画面上では非表示。送信された場合は対象年齢の上限として保持 |
| `tag` | 任意(複数指定可) | タグID。`create`: 省略時は空。`update`: `tag`キーが1つも無ければ既存のタグ構成を維持、1つでもあればその内容で全置換 |
| `notify_enabled` | 任意 | `"on"`/`"true"`/`"1"`/`"True"`/`"yes"`のみTrue、それ以外は明示的にFalse。**`create`でキー自体が無い場合はモデルのdefault=Trueを維持**(意図せずOFFにしないため)。`update`でキー自体が無い場合は既存値を維持 |

いずれの操作も成功・失敗にかかわらず`redirect("search:search_results")`
(Post/Redirect/Getパターン、クエリ条件は保持しない単純な形)。

### 2.2 `/notifications/`(`notifications`アプリ、`app_name="notifications"`)

| URL名 | パス | メソッド | 認証 | 説明 |
|---|---|---|---|---|
| `notifications:notification_list` | `/notifications/` | GET | `@login_required` | 本人の通知一覧(`notifications`)と未読件数(`unread_count`)を表示。テンプレート: `notifications/templates/notifications/notification_list.html` |
| `notifications:notification_mark_read` | `/notifications/<int:pk>/read/` | POST(`@require_POST`) | `@login_required` | 指定通知を個別既読化。本人以外の通知を指定した場合は`PermissionError`が握りつぶされ何も起きない(リダイレクトのみ) |
| `notifications:notification_mark_all_read` | `/notifications/read-all/` | POST(`@require_POST`) | `@login_required` | 本人の未読通知を一括既読化 |

いずれも処理後`redirect("notifications:notification_list")`。

**注意**: `notification_list`等は`@login_required`のため、未認証アクセスは
Djangoの既定ログインURL(`/accounts/login/`)へ302リダイレクトされるが、本プロジェクトには
`accounts`アプリが未導入のため`/accounts/login/`自体が404になる(セクション5参照)。

## 3. モデル仕様

### 3.1 `SavedSearch`(`search/models.py`)

| フィールド | 型 | null/blank | default | 備考 |
|---|---|---|---|---|
| `owner` | `ForeignKey(settings.AUTH_USER_MODEL)` | (必須) | - | `on_delete=CASCADE`, `related_name="saved_searches"` |
| `keyword` | `CharField(max_length=100)` | `blank=True` | `""` | |
| `location` | `CharField(max_length=255)` | `blank=True` | `""` | |
| `period_from` | `DateField` | `null=True, blank=True` | `None` | 未指定=期間制限なし |
| `period_to` | `DateField` | `null=True, blank=True` | `None` | 未指定=期間制限なし |
| `age_min` | `PositiveIntegerField` | `null=True, blank=True` | `None` | 入力欄は非表示。既存条件との互換性のため内部では使用する |
| `age_max` | `PositiveIntegerField` | `null=True, blank=True` | `None` | 入力欄は非表示。既存条件との互換性のため内部では使用する |
| `tags` | `ManyToManyField("events.Tag")` | `blank=True` | - | `related_name="saved_searches"`。中間モデルなし(素のM2M) |
| `priority` | `CharField(max_length=20)` | `blank=True` | `""` | 未使用の予約フィールド(choices未確定) |
| `notify_enabled` | `BooleanField` | - | `True` | Falseなら`EventMatchNotifier`の走査対象外 |
| `created_at` | `DateTimeField` | - | `auto_now_add=True` | |
| `updated_at` | `DateTimeField` | - | `auto_now=True` | |

`Meta.ordering = ["-created_at"]`。`clean()`で以下を検証(`full_clean()`経由、
`SavedSearchService`が呼び出す):
- `period_from > period_to`なら`ValidationError`
- `age_min > age_max`なら`ValidationError`

### 3.2 `Notification`(`notifications/models.py`)

| フィールド | 型 | null/blank | default | 備考 |
|---|---|---|---|---|
| `user` | `ForeignKey(settings.AUTH_USER_MODEL)` | (必須) | - | `on_delete=CASCADE`, `related_name="notifications"` |
| `event` | `ForeignKey("events.Event")` | (必須) | - | `on_delete=CASCADE`, `related_name="notifications"` |
| `saved_search` | `ForeignKey("search.SavedSearch")` | (必須) | - | `on_delete=CASCADE`, `related_name="notifications"` |
| `notification_type` | `CharField(max_length=20, choices=NotificationType.choices)` | - | `NotificationType.MATCH`(`"match"`) | 現状choicesは`match`(条件一致)のみ |
| `message` | `CharField(max_length=255)` | (必須) | - | |
| `is_read` | `BooleanField` | - | `False` | |
| `created_at` | `DateTimeField` | - | `auto_now_add=True` | |

`Meta.ordering = ["-created_at"]`、`Meta.constraints`に
`UniqueConstraint(fields=["user", "event", "saved_search"], name="uniq_match_notification")`
があり、同一ユーザー・イベント・保存検索の組み合わせで通知を二重生成できない
(DBレベルの制約)。

## 4. サービス層API

### `search/services.py`

- **`SearchService.search(criteria: SearchCriteria) -> QuerySet[Event]`**
  `search/queries.py::published_events()`(`status`が`DRAFT`/`CANCEL`のイベントを
  除外)を起点に、`criteria`の非空フィールドのみを`Q`でAND結合して絞り込む
  (`keyword`はtitle/descriptionへのOR、`tag`は複数指定時OR)。空条件なら全公開
  イベントをそのまま返す。
- **`SavedSearchService.create(*, owner, tag_ids=None, **fields) -> SavedSearch`**
  `full_clean()`実行後保存。`tag_ids`指定時は`tags.set(...)`。
- **`SavedSearchService.update(*, saved_search, user, tag_ids=None, **fields) -> SavedSearch`**
  `user != saved_search.owner`なら`PermissionError`。それ以外は`fields`を
  `setattr`で反映し`full_clean()`→保存。
- **`SavedSearchService.delete(*, saved_search, user)`**
  `user != saved_search.owner`なら`PermissionError`。
- **`MatchService.matches(saved_search, event) -> bool`**
  `saved_search`と`event`が条件的に一致するかどうかを判定する。
  `SearchService.search()`のSQLフィルタと同じ判定基準になるよう、`search/logic.py`
  の`period_overlaps`/`age_ranges_overlap`を共有している。対象年齢の入力欄は
  非表示だが、既存の保存条件との互換性のため内部判定は維持する。

### `notifications/services.py`

- **`should_notify(user) -> bool`**
  暫定で常に`True`(セクション5参照)。
- **`NotificationService.create_notification(*, user, event, saved_search, message, notification_type=Notification.NotificationType.MATCH) -> Notification`**
  `get_or_create`(重複防止)。
- **`NotificationService.mark_as_read(*, notification, user) -> Notification`**
  `notification.user != user`なら`PermissionError`。
- **`NotificationService.mark_all_as_read(*, user) -> int`**
  更新件数を返す。
- **`NotificationService.get_notifications(*, user) -> QuerySet[Notification]`**
- **`NotificationService.unread_count(*, user) -> int`**
- **`EventMatchNotifier.notify_for_event(event) -> list[Notification]`**
  `notify_enabled=True`の`SavedSearch`を全走査し、`should_notify`と
  `MatchService.matches`の両方を満たす場合のみ`Notification`を
  `get_or_create`で作成(既存なら何もしない)。**新規作成された**
  `Notification`のリストを返す(既存だったものは含まない)。

### 他アプリからの利用例

**例1: イベント作成後に一致通知を発火させる(`events`アプリ等から呼ばれる想定)**

```python
from notifications.services import EventMatchNotifier

event = EventService.create_event(organizer=request.user, **fields)
EventMatchNotifier.notify_for_event(event)  # 一致する保存検索の持ち主に通知を作成
```

**例2: 他アプリのビューから検索結果を取得したい場合**

```python
from search.criteria import SearchCriteria
from search.services import SearchService

criteria = SearchCriteria(keyword="花火", tag_ids=[1, 2])
events = SearchService.search(criteria)  # QuerySet[Event]
```

## 5. 既知の制約・TODO

- **`should_notify`は暫定で常に`True`**(`notifications/services.py`)。
  `# TODO: notifications_enabled連携待ち`とコメントしている通り、`accounts`アプリ
  導入後にユーザーの通知可否設定(`notifications_enabled`)と連携する予定(未着手)。
- **`accounts`アプリが本ブランチに未導入**のため、Django標準の`AUTH_USER_MODEL`
  (`django.contrib.auth.models.User`)をそのまま使っている。これに伴い
  `@login_required`のデフォルトログインURL`/accounts/login/`が**404**になる
  (ワイヤリングされていないため)。ブラウザでの手動確認時は、Django管理サイトの
  ログイン画面(`/admin/login/`)でセッションを張ってから`/search/`・
  `/notifications/`にアクセスすること。
- **タイムゾーンの扱いに注意**: `SearchService.search()`は`end_datetime__date__gte`/
  `start_datetime__date__lte`という`__date`ルックアップを使っており、これは
  `settings.TIME_ZONE`(`"Asia/Tokyo"`)へ変換してから日付を取り出す。一方
  `MatchService.matches()`はPython側で`timezone.localtime(event.start_datetime).date()`
  を使っており、意図的に同じ「現在のタイムゾーンでの日付」に揃えている。
  過去、`MatchService`側が素の`event.start_datetime.date()`(`USE_TZ=True`環境では
  UTC基準)を使っていたためJST 00:00〜09:00開始のイベントで`SearchService`と
  判定がズレるバグがあり、修正済み・回帰テスト
  (`search/tests/test_services.py::test_search_service_and_match_service_agree_on_jst_date_boundary`)
  も追加済み。**新しく期間・日時関連のロジックを追加する際は、この`__date`
  ルックアップと`timezone.localtime().date()`の対応関係を崩さないこと。**
- **`/search/`は元々`core/urls.py`の`search_results`という同名プレースホルダーに
  URLが横取りされていた**。ユーザー承認のもと`core/urls.py`の該当1行と
  `core/views.py`の`search_results`関数のみを削除して解消済み(`core`の他機能は
  無変更)。
- **`search/search_results.html`・`notifications/notification_list.html`は
  動作確認用の簡易UI**であり、装飾・実運用向けのデザインは未実装(画面担当の対象)。

## 6. 開発・テスト

### テスト実行

```bash
.venv/bin/python manage.py test search notifications
# core(URL配線に関わる)も含めて確認する場合:
.venv/bin/python manage.py test search notifications core
```

テスト構成:
- `search/tests/test_logic.py`: 純粋ロジック、標準`unittest`。
- `search/tests/test_models.py`・`search/tests/test_services.py`・
  `search/tests/test_views.py`: Django `TestCase`。
- `notifications/tests.py`: モデル・サービスのDjango `TestCase`(単一ファイル)。

その他の確認コマンド:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

### デモデータ投入

`search/management/commands/seed_demo_data.py`(冪等・再実行可能)で、
ブラウザ手動確認用のテストユーザー・タグ・イベント・保存検索・通知を投入できる。

```bash
.venv/bin/python manage.py seed_demo_data
```

投入されるテストユーザー: `demo-participant@example.com` /
`demo-organizer@example.com`(パスワードはいずれも`testpass123`)。
詳細は同コマンドのソースを参照。
