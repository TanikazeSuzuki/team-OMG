# Diagram

このフォルダ配下の `.mmd` ファイルは [Mermaid](https://mermaid.ai/) 形式で作成されています。
閲覧、編集は VSCode の Mermaid プラグイン を利用することをおすすめします。
Mermaid プラグイン: https://marketplace.visualstudio.com/items?itemName=MermaidChart.vscode-mermaid-chart
Mermaid 公式ドキュメント: https://mermaid.ai/docs

3ファイル(`class.mmd` / `er.mmd` / `screen.mmd`)はいずれも現在のコードベースに追従済みです。

## 各ファイルの説明

### [class.mmd](class.mmd): クラス図

対象スコープは **モデル層・サービス層・フォーム層(`accounts/forms.py`)** です。各アプリの
`views.py`(CBV/関数ビュー)は意図的にスコープ外としています。画面・ビュー遷移は `screen.mmd`
側で扱います。

### [er.mmd](er.mmd): ER図

全5アプリ(accounts / events / interactions / search / notifications)の全モデルを対象にしています。
エンティティ名は Django の実テーブル名(例: `accounts_user`, `events_event`)ではなく、モデル名由来の
snake_case 論理名(`user`, `event`, `event_tag` など)を使用しています。詳細な命名規則・注記は
`er.mmd` 冒頭のコメントを参照してください。

### [screen.mmd](screen.mmd): 画面遷移図

画面の採否は以下のルールに基づいています。

1. URL(`urls.py`)・ビュー(`views.py`)・テンプレートが実在し、実際にrenderされている画面 → 通常ノードとして含める。
2. URLとビューは実在するが中身が未実装のスタブ → 含めるが、ノードラベルに「(未実装)」と注記する。
3. どのビューからも参照されない孤立テンプレート → 図には含めない。

また、画面(ページ)そのものではないテンプレートもノード化していません。
現在図から除外しているファイルは以下のとおりです。

| 除外ファイル | 理由 |
| --- | --- |
| `templates/events/_event_card.html` | 独立した画面ではなく、一覧系画面から `{% include %}` される部品(パーシャル) |

除外理由の調査根拠(URL解決・テンプレート解決の実地検証手順など)は `screen.mmd` 冒頭のコメントに
詳しく記載しています。
