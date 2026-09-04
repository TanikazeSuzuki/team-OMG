# 担当2 (events / interactions) 受け渡しドキュメント

## 担当3へ：イベントの公開状態、フィールド、評価集計の参照方法

### 公開イベントの取得方法
下書き・中止を除いた公開イベントのみを取得するには、`EventService.get_published_events()` を使ってください。

```python
from events.services import EventService

published_events = EventService.get_published_events()
```

直接 `Event.objects.filter(status=Event.Status.PUBLISH)` としても同じ結果になりますが、フィルタ条件が変わる可能性があるためサービス層経由を推奨します。

### Eventモデルの主なフィールド
| フィールド名 | 型 | 説明 |
|---|---|---|
| title | CharField | イベント名 |
| explanation | TextField | 説明文 |
| organizer | ForeignKey(User) | 主催者 |
| start_datetime / end_datetime | DateTimeField | 開始・終了日時 |
| location | CharField | 開催場所 |
| min_age / max_age | PositiveIntegerField | 対象年齢(任意) |
| image | ImageField | 見出し画像(任意) |
| status | CharField | draft / publish / cancel |
| tags | ManyToManyField(Tag) | タグ(EventTag経由) |

### 評価・集計の取得方法
```python
from interactions.services import InteractionService

stats = InteractionService.get_event_stats(event)
# stats["average_rating"], stats["review_count"],
# stats["favorite_count"], stats["like_count"]
```

---

## 担当4へ：一覧・詳細・お気に入り・評価・レビュー用のURL、フォーム、コンテキスト

### URL一覧
| URL | 名前 | メソッド | 説明 |
|---|---|---|---|
| /events/ | events:event_list | GET | 公開イベント一覧 |
| /events/<pk>/ | events:event_detail | GET | イベント詳細 |
| /events/mine/favorites/ | events:my_favorites | GET(要ログイン) | 自分のお気に入り一覧 |
| /events/mine/history/ | events:my_view_history | GET(要ログイン) | 自分の閲覧履歴 |
| /interactions/events/<pk>/favorite/ | interactions:toggle_favorite | POST(要ログイン) | お気に入り登録/解除 |
| /interactions/events/<pk>/like/ | interactions:toggle_like | POST(要ログイン) | いいね登録/解除 |
| /interactions/events/<pk>/review/ | interactions:submit_review | POST(要ログイン) | 評価・レビュー投稿(rating, comment) |

### テンプレートに必要なファイル(担当4で作成)
- `templates/events/event_list.html` — コンテキスト: `events`
- `templates/events/event_detail.html` — コンテキスト: `event`, `stats`, `is_favorited`, `is_liked`
- `templates/events/my_favorites.html` — コンテキスト: `events`
- `templates/events/my_view_history.html` — コンテキスト: `views`(EventViewのQuerySet)

### 注意点
- お気に入り・いいね・評価はPOSTのみ(GETでは動きません)
- 評価・レビューはイベント終了後のみ投稿可能。フォーム側で開催前は投稿ボタンを非表示にするなどのUI配慮を推奨
- レビュー文章(comment)は任意項目。UIに含めるかは要チーム確認

---

## 担当5へ：主催者用作成・編集・削除画面のURLとフォーム

**変更点**: イベント作成は運営がDjango管理画面(`/admin/`)で代行登録する運用になったため、一般ユーザー向けの作成・編集・削除画面(EventForm等)は不要になりました。担当5の作業範囲からは除外されます。

---

## 担当6へ：必要なイベント、タグ、評価、レビューのテストデータ条件

### イベント
- 公開状態(publish)のものを複数作成してください(下書き・中止も動作確認用に数件あると良い)
- 一部は開始日時が未来、一部は終了日時が過去(評価テスト用)にしてください
- 年齢制限(min_age, max_age)あり/なしの両パターンがあると良い

### タグ
- 複数のタグを作成し、1イベントに複数タグを紐付けてください(EventTag経由)

### 評価・レビュー
- **終了済みイベントに対してのみ**評価データを作成してください(開催前イベントへの評価はモデル制約でエラーになります)
- 星評価は0〜5の範囲で複数パターン用意してください
- 同一ユーザー・同一イベントの組み合わせは1件までです(重複不可)