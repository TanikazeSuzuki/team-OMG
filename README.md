# team-OMG グルメ店決めアプリ

Django + SQLite + Django Templateで開発するための初期ファイルです。

## 現在の状態

- Djangoの設定、3つのapp、共通画面、ログイン画面、担当資料を用意しています。
- Python・Djangoの実インストールとサーバー起動は未検証です。初回に下のセットアップを実行してください。
- グループ作成・店舗評価・投票などの機能はこれから実装します。

## Windowsでのセットアップ

1. このリポジトリを任意の作業場所へcloneします。Gitとインターネット接続、Windows x64環境が必要です。
2. `setup.cmd` をダブルクリックします。初回はインターネット接続が必要です。
3. 最後に `Setup completed` と表示されたら `start.cmd` をダブルクリックします。
4. ブラウザーで http://127.0.0.1:8000/ を開きます。サーバーの停止は Ctrl+C です。

PowerShellから実行する場合：

```powershell
git clone https://github.com/TanikazeSuzuki/team-OMG.git team-OMGapp
cd team-OMGapp
.\setup.cmd
.\start.cmd
```

仮想環境のActivate.ps1は実行しません。Pythonは常に `.venv\Scripts\python.exe` を指定します。

## セットアップが行うこと

1. CPythonの公式NuGetパッケージから **Python 3.13.15 / Windows x64** を `.tools/python-3.13.15/` へ展開します。
2. プロジェクト専用の `.venv` を作ります。
3. `requirements.txt` から **Django 5.2.17** とその依存パッケージを導入します。
4. Django標準のmigrationをSQLiteへ適用します。
5. `pip check` と `manage.py check` を実行します。失敗した場合は途中で停止します。

これらはセットアップで導入するバージョンです。各自のPCで導入・起動を確認してください。
管理者権限やシステムのPATH変更を前提とせず、Python本体もこのフォルダ内に置く構成です。
Djangoは固定版ですが、間接依存の解決結果は `.setup-installed.txt` に記録します。
全員の間接依存まで固定する場合は、最初の成功環境で確認した一覧をrequirements.txtに反映して共有します。

**.toolsはセットアップ後も必要です。** 仮想環境は元のPython本体を参照するため削除しないでください。
フォルダを別の場所へ移動した場合、.venvは再作成が必要になる場合があります。

## 管理ユーザーとログイン

パスワードは各自で設定します。共通の初期パスワードは作成しません。

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

- 開発用トップ： http://127.0.0.1:8000/
- ログイン： http://127.0.0.1:8000/accounts/login/
- 管理画面： http://127.0.0.1:8000/admin/

標準Userを使用します。管理画面から開発用ユーザーを追加できます。
ログアウトはCSRF付きPOSTです。現段階で新規登録・パスワード再設定の画面はありません。

## 担当と構成

| app | 担当 | 今後実装するもの |
| --- | --- | --- |
| groups | 佐々木 | Group / GroupMember / UserPreference |
| restaurants | 村瀬 | Restaurant / Evaluation / EvaluationReason / 候補絞り込み / 再検索 |
| voting | 佐々木 | Vote / 最終投票 / 最終結果 |

- `config/settings.py`：3 apps、ルートのtemplates/static、日本語、Asia/Tokyoを設定済みのソース。
- `config/urls.py`：開発用トップ・ログイン・ログアウト・管理画面・各appのURLを接続。
- 各appの `urls.py`：接続先の空ファイル。業務機能のURLは未追加です。
- `templates/base.html`、`home.html`、`registration/login.html`：最小画面。
- `static/css/common.css`：共通CSS。
- `docs/全員共通_必要ファイル.txt`：必要ファイルの一覧・共有ルール。
- `docs/佐々木.txt`、`docs/村瀬.txt`：各担当の仕様・順序・完了条件。

Model・Form・service・業務画面・ダミー店舗のfixtureは今後追加します。
空のtests.pyはテスト実装済みを意味しません。

## MVPの順番

ダミー店舗で条件入力 → 候補表示 → 評価 → 最終投票 → 結果までつなぎ、
その後に評価理由からの簡単な再検索を追加します。**外部店舗APIは後回し**です。
Restaurantの項目が決まる前にfixtureは作成しません。
村瀬が `restaurants/fixtures/restaurants_demo.json` などを追加した時点で投入手順を追記します。

## 機能開発時によく使うコマンド

Modelを変更した人：

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Modelとmigrationを一緒にGitで共有します。変更を受け取った人は `migrate` を実行します。
他の人のmigrationを作り直したり、競合を隠すために削除したりしません。
業務テストを実装した後は `manage.py test` で実行します。

Gitで共有するもの：ソース、templates、static、requirements.txt、migrations、docs。
共有しないもの：.tools、.venv、db.sqlite3と一時ファイル、キャッシュ、秘密情報。
setup.cmd自体はGitへのコミット・pushを行いません。

## セットアップに失敗した場合

- ダウンロード失敗：画面に出たエラーを確認し、NuGetとPyPIへ接続できる環境で再実行します。
- 壊れた仮想環境：サーバーを止め、プロジェクト内の `.venv` を `.venv.backup` など未使用の名前へ変更してから再実行します。db.sqlite3やソースは残します。
- Python本体の検証失敗：プロジェクト内の `.tools/python-3.13.15` を別名で退避してから再実行します。.venvも作り直してください。
- 既にサーバーが動いている：起動済みターミナルでCtrl+Cを押してから再起動します。
- OneDriveで競合したDBは共有せず、各自のローカルDBを使います。

このsettings.pyはローカル開発用です。公開時には秘密鍵・DEBUG・DB・静的ファイルなどを本番向けに設定します。
.envは採用していません。置くだけでは読み込まれません。

## 確認元

- Python公式のNuGet配布説明：https://docs.python.org/3.13/using/windows.html#the-nuget-org-packages
- 使用するPythonパッケージ：https://www.nuget.org/packages/python/3.13.15
- 使用するDjango：https://pypi.org/project/Django/5.2.17/
- Django Windows導入：https://docs.djangoproject.com/ja/5.2/howto/windows/
