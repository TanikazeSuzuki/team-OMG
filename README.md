# Team-D

Djangoを使ったイベント共有アプリの学習用プロジェクトです。

## 現在の学習範囲

現在は画面のひな型に加え、担当1のアカウント基盤を実装しています。

- `templates/core/home.html`
- `templates/core/search_results.html`
- `templates/core/event_form.html`
- `templates/core/review_form.html`
- `templates/core/event_detail.html`
- `templates/core/review_detail.html`
- `static/css/style.css`
- `core/views.py`
- `core/urls.py`
- `core/forms.py`
- `core/tests.py`
- メールアドレスをログインIDとするカスタムユーザー
- 一般参加者・主催者・管理者の区分
- ユーザー設定（希望地域、通知可否、テーマ）
- 登録、ログイン、ログアウト、プロフィール変更、設定、退会のバックエンド
- 主催者権限用の`OrganizerRequiredMixin`
- アカウント機能の自動テスト

アカウント画面のテンプレートはフロントエンド担当が追加します。担当間の接続方法は
`docs/担当1_接続仕様.md`を参照してください。

## 必要な環境

- Python 3.10以上（Python 3.14で動作確認）
- Django 5.2 LTS

## セットアップ

Windows PowerShellの場合:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

ブラウザで <http://127.0.0.1:8000/> を開いてください。管理画面は
<http://127.0.0.1:8000/admin/> です。

管理ユーザーを作る場合:

```powershell
python manage.py createsuperuser
```

## テスト

```powershell
python manage.py test
```

## 構成

```text
config/             プロジェクト全体の設定
core/               画面用の空ファイルを置くアプリ
accounts/           ユーザー、認証、設定、権限
templates/          HTMLテンプレート
static/             CSSなどの静的ファイル
docs/               担当間の接続仕様
manage.py           Django管理コマンドの入口
requirements.txt    Python依存パッケージ
```

## 環境変数

本番環境では次の環境変数を設定してください。

- `DJANGO_SECRET_KEY`: 十分に長いランダムな秘密鍵
- `DJANGO_DEBUG`: 本番では `false`
- `DJANGO_ALLOWED_HOSTS`: カンマ区切りの許可ホスト名
