# reve-writer
(作成者) Revetronique
(作成日) 2026/6/17

## 概要

運用しているWordPressブログの記事自動生成システム。
Claude Code → Notion → WordPress のパイプライン。
カスタムコードは使わない。Notion + CLAUDE.md + MCP で完結。

---

## ローカル設定

NotionページURLなど環境固有の値は `CLAUDE.local.md`（Git管理外）に記載する。
存在しない場合は `CLAUDE.local.md.example` をコピーして作成すること。

@CLAUDE.local.md

---

## Notion DB構成

| DB | 役割 | 主な用途 |
|---|---|---|
| ラブライブ作品別DB | 作品マスター | ラブライブシリーズの作品情報 |
| 聖地スポットDB | スポットマスター | 聖地の位置・情報（座標はWGS84 小数点6桁） |
| 登場シーンDB | 登場情報 | スポット × 話数/MV（1登場=1レコード） |
| ご当地コラボDB | コラボ情報 | 聖地巡礼先の現地で行われている作品とのコラボをまとめたデータ |
| 来訪記録DB | 巡礼ログ | 訪問記録（Status: Draft/Writing/Published） |
| 下書き | 記事下書き置き場 | reve-writerが生成した下書きを保存。Claude Codeが取得してWordPressに投稿する |
| Claude Code 連携ルール | システム連携 | reve-writerとNotion、Claude Codeの連携についてまとめたドキュメント |

### 下書きページ構造

- 親ページURL: `CLAUDE.local.md` に記載（このファイルはGit管理外）
- 1記事につき1ページ作成
- タイトル形式: `YYYY-MM-DD_{スラッグ}`（例: `2026-06-04_event-makerfaire-tokyo-2026`）

各ページの冒頭に以下のメタ情報をテキストブロックで記載する:

```
ステータス: 下書き生成済み
記事タイプ: Type D
スラッグ: event-makerfaire-tokyo-2026
カテゴリ: イベントレポート
メタディスクリプション: （120文字以内）
NAS写真フォルダ: photos/events/2026-06-makerfaire/
選定写真リスト: makerfaire-venue-01.jpg(id:1234|url:https://...), makerfaire-keyboard-01.jpg(id:1235|url:https://...)
---
（ここより後のみが本文）
```

その後に本文（Gutenbergブロック形式）を続ける。

ステータスの遷移:
- `下書き生成済み` → reve-writerが書き込んだ直後
- `投稿済み` → Claude CodeがWordPressにPOSTした後に更新

### Visits DB プロパティ（写真関連）

| プロパティ | 型 | 説明 |
|---|---|---|
| 写真フォルダ | Text | NASパス（例: photos/pilgrimage/sunshine/numazu/2024-03/） |
| 選定写真リスト | Text | ファイル名・id・urlをセットで（例: spot-uchi-harbor-01.jpg(id:1234\|url:https://...)） |

### Events DB プロパティ

| プロパティ | 型 | 説明 |
|---|---|---|
| イベント名 | Title | 正式名称 |
| 日付 | Date | 開催日 |
| 場所 | Text | 会場名＋住所 |
| 座標 | Text | WGS84 小数6桁（Google Maps右クリックでコピー） |
| カテゴリ | Select | イベントレポート / お出かけレポート / ライブレポート |
| 記事タイプ | Select | Type D / Type E |
| ステータス | Select | 予定 / メモ収集中 / 素材整理中 / 素材整理完了 / 執筆中 / レビュー待ち / 公開済み |
| 記事URL | URL | 公開後に記入 |
| 写真フォルダ | Text | NASパス（例: photos/events/2026-06-makerfaire/） |
| 写真選定リスト | Text | 使用するファイル名をカンマ区切りで（例: makerfaire-keyboard-01.jpg, makerfaire-booth-01.jpg） |
| メモ | Text（本文） | 現地メモ + 帰宅後の補完 |
| 見出し構成 | Text | H2/H3の箇条書き構成 |
| 録音ファイル | Text | NASパスまたは「なし」 |
| 公開期限 | Date | 鮮度目標日（イベント日+2日） |
| アフィリエイト候補 | Multi-select | Amazon / Rakuten / BOOTH / その他 |

---

## 記事タイプ一覧

| タイプ | 用途 | DB | テンプレート |
|---|---|---|---|
| Type A | 聖地巡礼 総合ガイド（SEO軸） | Visits DB | 後述 |
| Type B | 聖地巡礼 写真比較・レポート | Visits DB | 後述 |
| Type C | 聖地巡礼 アクセス・実用情報 | Visits DB | 後述 |
| Type D | イベントレポート | Events DB | 後述 |
| Type E | お出かけレポート | Events DB | 後述 |

---

## 共通制約

- WordPress投稿は**必ず draft**。公開は手動。
- 写真のバイナリデータを Claude API に送信しない。
- NASアクセスは SMB マウント（LAN内のみ）。`ls` によるファイル名取得のみ行う。
- アップロード前にユーザー確認を必ず挟む。
- アニメのスクリーンショットは使用しない（著作権リスク）。

---

## 文章スタイル（全記事タイプ共通）

Notion の Writing Style ページも参照のこと。

### 基本ルール

- 冒頭: 「どうも、Reveです。」
- 締め: 「もし参考になれば幸いです。」
- 見出し: 【】形式（例: 【会場の様子】）
- 一人称: 「当方」または省略
- 読者: 皆さん
- 語尾: です・ます調、会話的で丁寧だが堅すぎない
- 適度にカジュアル表現を混ぜる:（汗）、ｗ、「〜なんですよね」等
- 段落は3〜4文で改行（読みやすさ重視）
- 記事の長さ: 2,000〜2,500文字を目安（SiteGuard LiteのボディサイズPOST制限があるため、過度に長くしない）

### 写真の挿入ルール

- 各セクションに1〜3枚
- キャプション付き
- 選定写真リストのファイル名でNASパスと照合

### メモ → 文章の変換ルール

メモの箇条書きを文章化する際のルール:

```
【メモ（入力）】
- Cherry MX互換、基板4層、KiCad設計
- 価格 ¥12,000（BOOTH販売あり）
- 感想: キーキャップの触り心地が独特

【文章化（出力）】
こちらはCherry MX互換のスイッチを採用した自作キーボードで、
基板は4層構成、KiCadで設計されているとのこと。
価格は12,000円で、BOOTHでも販売されています。
実際に触らせていただいたのですが、キーキャップの触り心地が
独特で、これは好みが分かれそうなところですね。
```

変換時の注意:
- メモの箇条書きをそのまま並べただけの文章にしない
- 「〜とのこと」「〜だそうです」で伝聞と体験を区別する
- 感想メモは「実際に〜してみたのですが」等の体験描写に展開する
- 数字・固有名詞はメモの記載をそのまま保持（勝手に変えない）
- メモに感想がないセクションでも、最低1文は所感を入れる
  → **[★要加筆: ここに感想を追記]** とプレースホルダーを置く

### プレースホルダーと加筆マーカー

テンプレートの `{{...}}` はNotionデータで自動置換する。
データが不足している場合は以下のマーカーを挿入し、人間の加筆を促す:

| マーカー | 意味 |
|---|---|
| `[★要加筆: 感想]` | メモに感想がなく、体験ベースの記述が必要 |
| `[★要加筆: 詳細]` | メモの情報が不足、現地の記憶で補完が必要 |
| `[★要確認: {{内容}}]` | 数字や固有名詞がメモから読み取れず確認が必要 |
| `[★写真: {{説明}}]` | 該当する写真がNAS内で見つからなかった |
| `[★アフィリエイト: {{種別}}]` | アフィリエイトリンクの挿入候補（人間が選定） |

WordPress下書きをエディタで開いた際、★マーカーを検索すれば加筆箇所が一覧できる。

---

## 記事タイプ別ルール

### 聖地巡礼記事（Type A/B/C）共通

- Visits DB から Status = "Draft" を取得
- ラブライブ作品別DB → 聖地スポットDB → 登場シーンDB のリレーションを辿る
- 同じ旅行の複数記事には共通の Series tag を付与
- 投稿時にナビカード用メニューに記事を自動追加
- 各記事末尾に `[navi_list name="メニュー名"]` を埋め込み

記事構成:
1. 挨拶 + 動機
2. 【今回の聖地巡礼について】概要テーブル
3. 【スポット名】× N — 各スポットの紹介
4. 【グルメ・お土産】（あれば）
5. 【まとめ】感想 + 次回予告
6. 【参考・アクセス情報】

### イベント記事（Type D）固有ルール

- Events DB から ステータス = "素材整理完了" を取得
- イベントの正式名称を必ず1回はフルで記載
- 各見どころセクションは「概要 → 詳細 → 感想」の3段構成
- 講演内容は要約のみ（引用する場合は発言者名と文脈を明記）
- 技術イベントではスペック・型番を正確に記載（メモの数字をそのまま使う）
- 「次回も行きたい」「来年は○○に注目」など前向きな締めを心がける

### お出かけ記事（Type E）固有ルール

- Events DB から ステータス = "素材整理完了" を取得
- アクセス情報を冒頭寄りに配置（読者がすぐ使える位置）
- 食事セクションは価格を必ず記載
- 季節・天候の影響がある場合は言及する
- 「○○がおすすめです」より「当方は○○が気に入りました」（押し付けない）

---

## Notion取得ルール

- 下書きページの取得は必ず `notion-fetch` でURLを直接指定する
- `notion-search` は使用禁止（全文検索になり低速のため）
- URLは引き渡しブロックの `Notionページ URL:` から読み取る

## 引き渡しブロック形式（reve-writer → Claude Code）

reve-writerがNotionに保存後、以下のフォーマットをチャットに出力する:

```
【Claude Codeへの引き渡し】
Notionページ URL: https://www.notion.so/{{ページのURL}}
スラッグ: {{スラッグ}}
記事タイプ: {{Type A / B / C / D / E}}
```

複数記事の場合は記事ごとに1ブロックずつ出力する。

## 記事タイプの判定

`notion-fetch` で取得したページのメタ情報ブロック（`---` より前）の
`記事タイプ:` フィールドを読み取り、以下のテンプレートを選択する：

| 記事タイプ | 使用テンプレート | 対応DB |
|---|---|---|
| Type A | 聖地巡礼 総合ガイド | Visits DB |
| Type B | 聖地巡礼 写真比較 | Visits DB |
| Type C | 聖地巡礼 アクセス情報 | Visits DB |
| Type D | イベントレポート | Events DB |
| Type E | お出かけレポート | Events DB |

記事タイプが読み取れない場合はユーザーに確認してから進む。

## 複数記事の並列処理

引き渡しブロックが複数ある場合は**オーケストレーターが全エージェントを直接管理**する（案B）。

```
オーケストレーター（Claude Code本体）
  フェーズ1（全記事×全エージェントを同時起動）:
  ├── photo-uploader（記事A） ─┐
  ├── photo-uploader（記事B） ─┤
  ├── proofreader（記事A）   ─┤ 全部並列
  └── proofreader（記事B）   ─┘
        ↓ 全完了後、確認画面を1回表示
  フェーズ2（ユーザー承認後）:
  ├── wp-poster（記事A） ─┐ 並列
  └── wp-poster（記事B） ─┘
```

- 直列処理は禁止
- 全記事の確認画面をまとめて**1回**表示してから承認を受ける
- `wp-poster` はユーザー確認後にのみ実行する

---

## 記事生成フロー

### 聖地巡礼記事（Type A/B/C）

**reve-writer（Claude.ai）が行う:**
1. 来訪記録DB から Status = "Draft" を取得
2. ラブライブ作品別DB → 聖地スポットDB → 登場シーンDB のリレーションを辿る
3. Writing Style ページからスタイルルールを取得
4. 下書き文章を生成
5. Notionの「下書き」ページに保存（タイトル: `YYYY-MM-DD_{スラッグ}`）

**Claude Code が行う（1コマンドで実行）:**
1. Notionの「下書き」ページからステータス = "下書き生成済み" のページを取得
2. **メタ情報と本文を分離する**（下記「Notion下書きページの分離ルール」を参照）
3. **写真マッチング**（後述）と **proofreader** を並列実行（→ サブエージェント構成参照）
4. マッチング結果と校正結果をまとめてユーザーに確認表示（確認は1回のみ）
5. 承認後、写真をアップロードしてGutenbergブロックに埋め込み
6. WP REST API で下書き投稿（本文のみ。メタ情報は各パラメータに振り分け）
7. ナビカード用メニューに記事を追加（シリーズ記事の場合）
8. Notionの下書きページのステータスを "投稿済み" に更新
9. 来訪記録DB の Status を "Writing" に更新、Article URL を記録

### イベント・お出かけ記事（Type D/E）

**reve-writer（Claude.ai）が行う:**
1. メモを受け取り、不足確認（1回）
2. 記事タイプ（Type D or E）に応じたGutenbergテンプレートで下書き生成
3. Notionの「下書き」ページに保存（タイトル: `YYYY-MM-DD_{スラッグ}`）

**Claude Code が行う（1コマンドで実行）:**
1. Notionの「下書き」ページからステータス = "下書き生成済み" のページを取得
2. **メタ情報と本文を分離する**（下記「Notion下書きページの分離ルール」を参照）
3. **写真マッチング**（後述）と **proofreader** を並列実行（→ サブエージェント構成参照）
4. マッチング結果と校正結果をまとめてユーザーに確認表示（確認は1回のみ）
5. 承認後、写真をアップロードしてGutenbergブロックに埋め込み
6. WP REST API で **下書き (status: draft)** 投稿（本文のみ。メタ情報は各パラメータに振り分け）
7. Notionの下書きページのステータスを "投稿済み" に更新
8. 「下書き投稿しました: [編集URL]」と表示

### Notion下書きページの分離ルール

Notionの下書きページを取得したら、**`---` より前のメタ情報ブロックと本文を必ず分離する。**
メタ情報は本文（contentパラメータ）に絶対に含めない。

| メタフィールド | 用途 |
|---|---|
| ステータス | 処理フラグのみ（投稿しない） |
| 記事タイプ | テンプレート選択に使用 |
| スラッグ | `slug` パラメータ |
| カテゴリ | `categories` パラメータ |
| メタディスクリプション | `meta.the_page_meta_description` |
| NAS写真フォルダ | 写真マッチングに使用 |
| 選定写真リスト | 写真マッチングに使用（id・url込みの場合は再アップロード不要） |

---

## 写真マッチングフロー

### 前提

- NASはSMBマウント済み（マウントポイントは後述）
- 写真のバイナリデータはClaude APIに送らない。`ls` によるファイル名取得のみ行う
- 選定写真リストが記入済みの場合はSTEP 1〜3をスキップしてSTEP 4から開始する

### STEP 1: フォルダ確認

Notion の `写真フォルダ` フィールドのパスを読み、`ls` でファイル一覧を取得する。

```powershell
# Windows（ネットワークドライブ）
ls "Y:\{Event|Travel|Pilgrimage}\{フォルダ名}\"

# macOS（SMBマウント）
ls "/Volumes/Photos/{Event|Travel|Pilgrimage}/{フォルダ名}/"
```

フォルダが存在しない・空の場合は `[★写真: フォルダが見つかりません（パス確認が必要）]` を挿入して次のステップへ。

### STEP 2: ファイル名マッチング

取得したファイル名と、記事で使うスポット名（聖地スポットDBのスラッグ）またはセクション名を文字列比較でマッチングする。

**聖地巡礼の場合:**
- ファイル名に `spot-{スラッグ}` が含まれるものを候補とする
- 例: スラッグ `uchi-harbor` → `spot-uchi-harbor-01.jpg` がマッチ

**イベント・お出かけの場合:**
- 選定写真リストに記載のファイル名と一致するものを候補とする
- リストが空の場合はフォルダ内の全ファイルを候補として提示する

### STEP 3: ユーザー確認

マッチ結果を以下の形式で表示し、承認を求める。承認なしにアップロードしない。

```
【写真マッチング結果】
スポット: 内浦港
  ✅ spot-uchi-harbor-01.jpg
  ✅ spot-uchi-harbor-02.jpg
スポット: ことりちゃんち
  ✅ spot-kotori-house-01.jpg
  ❌ 該当なし → [★写真: ことりちゃんちの写真が見つかりません]

承認する場合は「OK」、変更がある場合は指示をどうぞ。
```

### STEP 4: アップロードと埋め込み

承認後、PowerShell Jobsで全ファイルを**並列アップロード**する。
バイナリはNASから直接WPへ送信（Claude APIを経由しない）。

```powershell
$nasFolder = "Y:\{Event|Travel|Pilgrimage}\{フォルダ名}\"  # Notionの写真フォルダフィールドから取得
$files = @("spot-uchi-harbor-01.jpg", "spot-uchi-harbor-02.jpg", ...)

$jobs = $files | ForEach-Object {
  $fn = $_; $fp = $nasFolder + $fn
  Start-Job -ScriptBlock {
    param($url, $u, $p, $fp, $fn)
    & curl.exe -s `
      -X POST "$url/wp-json/wp/v2/media" `
      -u "${u}:${p}" `
      -H "Content-Type: image/jpeg" `
      -H "Content-Disposition: attachment; filename=$fn" `
      --data-binary "@$fp"
  } -ArgumentList $env:WP_SITE_URL, $env:WP_USERNAME, $env:WP_APP_PASSWORD, $fp, $fn
}

$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$results | ForEach-Object {
  $r = $_ | ConvertFrom-Json
  [PSCustomObject]@{ file = $r.slug; id = $r.id; url = $r.source_url }
} | Format-Table -AutoSize
```

取得した `id` と `source_url` をGutenbergの `{{photo_id}}` / `{{photo_url}}` に埋め込む。
一部失敗した場合は該当箇所に `[★写真: アップロード失敗]` を挿入する。

### STEP 5: Notionへの書き戻し（聖地巡礼のみ）

使用したファイル名を Visits DB の `選定写真リスト` フィールドに書き戻す。
次回の記事更新時に再マッチングの手間を省くため。

---

## NAS

写真はSynology NAS（DiskStation）に保存する。

### マウント方法

| OS | 方法 | パス |
|---|---|---|
| Windows | ネットワークドライブ割り当て（例: `Y:\`） | `\\DiskStation\Photos` |
| macOS | Finderからサーバー接続（SMB） | `smb://DiskStation/Photos` |

### フォルダ構造

```
\\DiskStation\Photos\
├── Event\                             ← 美術館・展示会・イベント・お出かけ等
│   └── {YYYY-MM-イベント名}\
├── Travel\                            ← 旅行写真
│   └── {YYYY-MM-目的地}\
└── Pilgrimage\                        ← 聖地巡礼写真（予定）
    └── {作品名}\
        └── {場所名}\
            └── {YYYY-MM}\
```

### ファイル命名規則

| 種別 | パターン | 例 |
|---|---|---|
| 聖地巡礼 | `spot-{スラッグ}-{連番2桁}.jpg` | `spot-uchi-harbor-01.jpg` |
| イベント・お出かけ | `{任意説明}-{連番2桁}.jpg` | `makerfaire-keyboard-01.jpg` |
| Travel | 命名規則なし（既存のまま） | — |

**ルール:**
- 聖地巡礼のスラッグは 聖地スポットDB の `スラッグ` フィールドと完全一致させる
- 連番は2桁ゼロ埋め（01, 02, … 10, 11）
- 区切り文字はハイフン1文字のみ。アンダースコアは使わない
- 拡張子は小文字（`.jpg` / `.png` / `.mp4`）

### 写真形式の前処理

iPhoneで撮影した写真がHEIC形式の場合、NASに保存する前にJPEGに変換する。

**単一ファイル:**
```bash
sips -s format jpeg input.HEIC -o output.jpg
```

**複数ファイル一括変換（macOS）:**
```bash
for file in *.HEIC; do
  sips -s format jpeg "$file" -o "${file%.HEIC}.jpg"
done
```

- `sips` はmac標準コマンド
- 変換後のJPEGは命名規則に従ってリネームしてからNASに保存する

### 写真フォルダフィールドの記入例

`\\DiskStation\Photos\` からの相対パスで記入する。

```
# Visits DB（聖地巡礼）
Pilgrimage\{作品名}\{場所名}\{YYYY-MM}\

# Events DB（イベント・お出かけ）
Event\{YYYY-MM-イベント名}\
```

### 過去写真（命名規則適用前）の扱い

GPS情報なし・ファイル名が不規則な古い写真は自動マッチングの対象外とする。
使用する場合は `選定写真リスト` に手動でファイル名を記入してからフローを実行する。

---

## パーマリンク

- 構造: `/%postname%/`
- Redirectionプラグインがパーマリンク変更を自動監視

### スラッグ命名規則

| 記事タイプ | パターン | 例 |
|---|---|---|
| 聖地巡礼 | `{location}-pilgrimage-{year}-{season}` | `numazu-pilgrimage-2026-spring` |
| 技術記事 | `{topic-keyword}` | `unity-quaternion-rotation` |
| DIY | `diy-{project-name}` | `diy-led-matrix-controller` |
| イベント (Type D) | `event-{english-event-name}-{year}` | `event-makerfaire-tokyo-2026` |
| お出かけ (Type E) | `visit-{english-destination}-{year}` | `visit-kozushima-2026` |

---

## WordPress投稿パラメータ

### 聖地巡礼記事

```json
{
  "title": "{{series}} 聖地巡礼 {{location}}編（{{year}}年{{season}}）",
  "content": "{{generated_gutenberg_html}}",
  "status": "draft",
  "slug": "{{english_slug}}"
}
```

### イベント記事（Type D）

```json
{
  "title": "【イベントレポート】{{event_name}}に行ってきた（{{year}}年）",
  "content": "{{generated_gutenberg_html}}",
  "status": "draft",
  "slug": "{{english_slug}}",
  "categories": ["{{category_id}}"],
  "tags": ["{{tag1}}", "{{tag2}}"],
  "meta": {
    "the_page_meta_description": "{{meta_description}}"
  }
}
```

### お出かけ記事（Type E）

```json
{
  "title": "【お出かけ】{{destination}} {{activity}}レポート（{{year}}年）",
  "content": "{{generated_gutenberg_html}}",
  "status": "draft",
  "slug": "{{english_slug}}",
  "categories": ["{{category_id}}"],
  "tags": ["{{tag1}}", "{{tag2}}"],
  "meta": {
    "the_page_meta_description": "{{meta_description}}"
  }
}
```

### メタディスクリプション

- 120文字以内
- 「場所/イベント名 + 何が見られるか + 一言感想」を含める
- 例: 「Maker Faire Tokyo 2026に行ってきました。個人開発の自作キーボードや基板が面白かった！会場の様子と見どころをレポートします。」

---

## シリーズ記事（ナビカード）

- 同じ旅行の複数記事には共通の Series tag を付与（Visits DB）
- 投稿時にナビカード用メニューに記事を自動追加
- 各記事末尾に `[navi_list name="メニュー名"]` を埋め込み

---

## 著作権の注意点

### 使えるもの（リスクが低い）
- 自分で撮影した現地の写真・動画
- 公式サイトへのリンク（URLのみ）
- アフィリエイトプログラム提供の商品画像（Amazon等）
- 公式YouTubeの埋め込み（埋め込みコード使用）

### 条件付き（引用の要件を厳密に守る）
- アニメのスクリーンショット: 1記事1〜2枚、最小サイズ
- 出所明記（例: ©プロジェクトラブライブ!サンシャイン!!）
- 自分の文章がメイン、画像は補足という関係を維持
- 引用の必然性がある文脈でのみ使用

### 避けるべきもの
- 公式ロゴの転載
- 公式イラストのそのままの掲載
- キャラクター画像をアイキャッチやヘッダーに使用
- ラブライブはKADOKAWA・ランティス・サンライズの複数社が権利保有

---

## Gutenbergブロックテンプレート

### 聖地巡礼記事（Type A/B/C 共通ベース）

```html
<!-- 導入 -->
<!-- wp:paragraph -->
<p>どうも、Reveです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{intro_text}}</p>
<!-- /wp:paragraph -->

<!-- 概要テーブル -->
<!-- wp:table {"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody>
<tr><th>作品</th><td>{{series}}</td></tr>
<tr><th>場所</th><td>{{location}}</td></tr>
<tr><th>訪問日</th><td>{{visit_date}}</td></tr>
<tr><th>アクセス</th><td>{{access}}</td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- ===== スポットセクション（繰り返し） ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【{{spot_name}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>（{{series}} {{episode}}）</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{spot_description}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":{{photo_id}},"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{photo_url}}" alt="{{spot_name}}" class="wp-image-{{photo_id}}"/>
<figcaption class="wp-element-caption">{{caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== /スポットセクション ===== -->

<!-- まとめ -->
<!-- wp:heading -->
<h2 class="wp-block-heading">【まとめ】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{conclusion}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もし参考になれば幸いです。</p>
<!-- /wp:paragraph -->

<!-- ナビカード（シリーズ記事の場合） -->
<!-- wp:shortcode -->
[navi_list name="{{menu_name}}"]
<!-- /wp:shortcode -->
```

### イベントレポート（Type D）

```html
<!-- wp:paragraph -->
<p>どうも、Reveです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{event_date}} に {{event_name}} に行ってきました。{{intro_text}}</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【イベント概要】</h2>
<!-- /wp:heading -->

<!-- wp:table {"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody>
<tr><th>イベント名</th><td>{{event_name}}</td></tr>
<tr><th>開催日</th><td>{{event_date}}</td></tr>
<tr><th>会場</th><td>{{venue}}</td></tr>
<tr><th>アクセス</th><td>{{access_info}}</td></tr>
<tr><th>入場料</th><td>{{admission}}</td></tr>
<tr><th>公式サイト</th><td><a href="{{official_url}}" target="_blank" rel="noopener noreferrer">{{official_url_display}}</a></td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>{{venue_atmosphere}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":{{photo_id}},"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{photo_venue_url}}" alt="{{event_name}} 会場の様子" class="wp-image-{{photo_id}}"/>
<figcaption class="wp-element-caption">{{venue_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== 見どころセクション（メモのセクション数に応じて繰り返し） ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【{{highlight_title}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{highlight_overview}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{highlight_detail}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":{{photo_id}},"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{highlight_photo_url}}" alt="{{highlight_title}}" class="wp-image-{{photo_id}}"/>
<figcaption class="wp-element-caption">{{highlight_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>{{highlight_impression}}</p>
<!-- /wp:paragraph -->

<!-- ===== /見どころセクション ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【会場グルメ・購入品】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{food_and_goods}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":{{photo_id}},"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{food_photo_url}}" alt="{{food_caption}}" class="wp-image-{{photo_id}}"/>
<figcaption class="wp-element-caption">{{food_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== アフィリエイトリンク挿入ポイント ===== -->
<!-- wp:paragraph -->
<p>{{affiliate_block}}</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【まとめ】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{summary}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もし参考になれば幸いです。</p>
<!-- /wp:paragraph -->
```

### お出かけレポート（Type E）

```html
<!-- wp:paragraph -->
<p>どうも、Reveです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{destination}} に行ってきたので、レポートします。{{intro_text}}</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【アクセス】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{access_detail}}</p>
<!-- /wp:paragraph -->

<!-- ===== アフィリエイト挿入ポイント: 交通系 ===== -->

<!-- ===== スポットセクション（訪問順に繰り返し） ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【{{spot_name}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{spot_description}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":{{photo_id}},"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{spot_photo_url}}" alt="{{spot_name}}" class="wp-image-{{photo_id}}"/>
<figcaption class="wp-element-caption">{{spot_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>{{spot_impression}}</p>
<!-- /wp:paragraph -->

<!-- ===== /スポットセクション ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【ランチ: {{restaurant_name}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{food_description}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"id":{{photo_id}},"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{food_photo_url}}" alt="{{restaurant_name}} {{menu_item}}" class="wp-image-{{photo_id}}"/>
<figcaption class="wp-element-caption">{{food_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== アフィリエイト挿入ポイント: グルメ系 ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【まとめ】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{summary}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もし参考になれば幸いです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【基本情報】</h2>
<!-- /wp:heading -->

<!-- wp:table {"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody>
<tr><th>場所</th><td>{{destination}}</td></tr>
<tr><th>住所</th><td>{{address}}</td></tr>
<tr><th>営業時間</th><td>{{hours}}</td></tr>
<tr><th>定休日</th><td>{{closed_days}}</td></tr>
<tr><th>料金</th><td>{{price}}</td></tr>
<tr><th>公式サイト</th><td><a href="{{official_url}}" target="_blank" rel="noopener noreferrer">{{official_url_display}}</a></td></tr>
<tr><th>Google Maps</th><td><a href="https://www.google.com/maps?q={{lat}},{{lng}}" target="_blank" rel="noopener noreferrer">地図を開く</a></td></tr>
</tbody></table></figure>
<!-- /wp:table -->
```

---

## Claude Code 呼び出しパターン

### 聖地巡礼記事

```
> 沼津の聖地巡礼記事を書いて。写真もアップロードして。
```

### Notion下書きから投稿（reve-writer連携後の標準フロー）

```
> Notionの下書きフォルダの最新ページを投稿して。
```

または特定の記事を指定:

```
> Notionの下書き「2026-06-04_event-makerfaire-tokyo-2026」を投稿して。
```

### 写真リネーム（新規写真をNASに追加した後）

```
> photos/pilgrimage/sunshine/numazu/2026-04/ の写真をリネームして。
```

Claude Codeが:
1. フォルダ内のファイル名一覧を `ls` で取得
2. 聖地スポットDB からスラッグ一覧を取得して候補を提示
3. 確認後に `mv` でリネーム実行
4. Visits DB の `選定写真リスト` に書き戻す

### イベント記事 — 基本（1コマンドで下書き生成）

```
> Events DBの「Maker Faire Tokyo 2026」から Type D で下書きを作って。
```

### イベント記事 — 写真なし（テキストのみ先に生成）

```
> Events DBの「Maker Faire Tokyo 2026」からテキストだけ下書きして。
> 写真は後で手動で入れる。
```

### イベント記事 — セクション再生成

```
> Events DBの「Maker Faire Tokyo 2026」のメモを更新したので、
> 見どころ②のセクションだけ再生成して。
```

### イベント記事 — 一括下書き

```
> Events DB でステータスが「素材整理完了」のイベントを全部
> 下書き生成して。写真は後で入れるのでテキストのみで。
```

### 既存投稿の修正

#### 特定セクションの書き直し

```
> 投稿ID 1234 の「自作キーボード」セクションを書き直して。
> キースイッチの説明をもう少し詳しくしたい。
```

Claude Codeが:
1. `GET /wp/v2/posts/1234` で全文取得
2. 該当Gutenbergブロックをブロックコメント（`<!-- wp:heading -->`等）で特定
3. 指示に従って該当ブロックの内容を差し替え
4. `POST /wp/v2/posts/1234` で全文更新
5. 「更新しました: [編集URL]」と表示

#### メタディスクリプションだけ変更

```
> 投稿ID 1234 のメタディスクリプションを「○○」に変えて。
```

#### タイトルとスラッグだけ変更

```
> 投稿ID 1234 のタイトルを「○○」、スラッグを「○○」に変えて。
```

**注意事項:**
- 投稿IDはWordPress管理画面のURL（`post.php?post=1234`）で確認する
- 全文POSTはConoHa WINGのデフォルト制限（32MB）に対して数十KB以下なので問題なし
- ファイル読み込みは `[System.IO.File]::ReadAllText` を使うこと（→ wp-poster技術仕様参照）
- 更新後は必ず編集URLで内容を目視確認する

### 公開前チェック

```
> 公開前チェックして
```

以下を自動確認:
1. タイトルにイベント名/場所と年が含まれるか
2. スラッグが英語で設定されているか
3. アイキャッチ画像が設定されているか
4. カテゴリ・タグが設定されているか
5. メタディスクリプションが記入されているか（120文字以内）
6. 全画像に alt 属性があるか
7. ★マーカーが残っていないか（残っていれば一覧表示）
8. 内部リンク候補の提案（過去記事から関連しそうなもの）
9. 文字数カウント（2,000〜3,000文字の目安内か）

---

## サブエージェント構成（reve-writer）

投稿ワークフローでは以下のサブエージェントを使用する：

| エージェント | 役割 | フェーズ |
|---|---|---|
| `photo-uploader` | NAS→WP Media APIへ並列アップロード | フェーズ1（並列） |
| `proofreader` | 文体・スタイルガイド準拠チェック | フェーズ1（並列） |
| `wp-poster` | WordPress REST API投稿 | フェーズ2（確認後のみ） |

**フェーズ1並列実行:** `photo-uploader` と `proofreader` は記事をまたいで全て同時起動してよい
**フェーズ2順次実行必須:** `wp-poster` はユーザー確認の完了後のみ実行

### 各エージェントの指示テンプレート

#### photo-uploader
```
以下を実行せよ:
- NAS写真フォルダ: {フォルダパス}
- 選定写真リスト: {ファイル名リスト}
上記フォルダの写真をWordPress Media APIに並列アップロードし、
取得したid・urlを一覧で返せ。
バイナリデータをClaude APIに送らないこと。
```

#### proofreader
```
以下の観点で下書きをチェックし、修正案を箇条書きで返せ:
1. 文体がCLAUDE.mdのスタイルガイドに準拠しているか
2. ★マーカーが残っていないか
3. 文字数が2,000〜2,500文字の範囲内か
4. 数字・固有名詞に誤りがないか
修正が必要な場合は該当箇所と修正案をセットで示せ。
```

#### wp-poster
```
ユーザーの承認後に以下を実行せよ:
1. photo-uploaderが返したid・urlをGutenbergブロックの{{photo_id}}・{{photo_url}}に埋め込む
2. WP REST APIで下書き投稿（status: draft）
3. Notionの下書きページのステータスを「投稿済み」に更新
4. 編集URLを表示
```

### ユーザー確認画面のフォーマット

単一記事の場合:

```
【確認】下書き投稿の準備ができました

📄 タイトル: 【イベントレポート】Maker Faire Tokyo 2026に行ってきた（2026年）
🔗 スラッグ: event-makerfaire-tokyo-2026
📂 カテゴリ: イベントレポート
🖼 写真: 5枚（アップロード済み）

【校正結果】
  ✅ 文体チェック: 問題なし  ✅ ★マーカー: 残りなし  ✅ 文字数: 2,340字

投稿してよければ「OK」、修正がある場合は指示をどうぞ。
```

複数記事の場合（フェーズ1完了後にまとめて1回表示）:

```
【並列投稿 確認】3記事の準備ができました

記事A: 【イベントレポート】Maker Faire Tokyo 2026...  🖼 5枚  ✅ 校正OK  ✅ 2,340字
記事B: 【お出かけ】神津島レポート...                  🖼 4枚  ✅ 校正OK  ⚠️ 2,610字（上限超過）
記事C: ラブライブ! 聖地巡礼 沼津編...                🖼 6枚  ✅ 校正OK  ✅ 2,180字

投稿してよければ「OK」、修正がある場合は記事名と指示を。
```

承認後の結果表示:

```
✅ 記事A → https://{WP_SITE_URL}/wp-admin/post.php?post=123&action=edit
✅ 記事B → https://{WP_SITE_URL}/wp-admin/post.php?post=124&action=edit
✅ 記事C → https://{WP_SITE_URL}/wp-admin/post.php?post=125&action=edit
```

### wp-poster 技術仕様

**環境変数（`.claude/settings.local.json` の `env` に設定済み）:**
- `WP_SITE_URL`: `$env:WP_SITE_URL`
- `WP_USERNAME`: WordPressユーザー名
- `WP_APP_PASSWORD`: Application Password

**投稿コマンド（Windows PowerShell 5.1）:**

```powershell
# コンテンツは [System.IO.File]::ReadAllText で読む（Get-Content -Raw は不可）
$content = [System.IO.File]::ReadAllText($htmlPath, [System.Text.Encoding]::UTF8)

$bodyObj = [ordered]@{
    title   = $title
    content = $content
    status  = "draft"
    slug    = $slug
    meta    = @{ the_page_meta_description = $metaDescription }
}
$json = $bodyObj | ConvertTo-Json -Depth 5

# BOMなしUTF-8 で書き出す（BOM付きだとWordPressがJSONパース失敗する）
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\wp-post.json", $json, $utf8NoBom)

# Invoke-RestMethod ではなく curl.exe を使う
$httpCode = & curl.exe -s -o "$env:TEMP\wp-response.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/wp/v2/posts" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: application/json; charset=utf-8" `
    --data-binary "@$env:TEMP\wp-post.json"

if ($httpCode -eq "201") {
    $resp = Get-Content "$env:TEMP\wp-response.json" -Raw | ConvertFrom-Json
    Write-Output "投稿ID: $($resp.id)"
    Write-Output "編集画面: $env:WP_SITE_URL/wp-admin/post.php?post=$($resp.id)&action=edit"
} else {
    Write-Output "エラー HTTP $httpCode"
    Get-Content "$env:TEMP\wp-response.json" -Raw
}
```

**注意:** SiteGuard LiteのPOSTボディサイズ制限があるため、記事本文は2,500文字以内に抑えること。制限内であればSiteGuardの無効化は不要。詳細は `wp-post-troubleshooting.md` 参照。
