---
name: post-draft
description: Notionの下書きページからWordPressへdraft投稿する標準フロー。reve-writerの引き渡しブロックを受け取ったとき、「Notionの下書き○○を投稿して」「下書きフォルダの最新ページを投稿して」等の投稿依頼で使用する。写真マッチング・校正・ユーザー確認・投稿・Notionステータス更新まで一貫して行う。
---

# post-draft — Notion下書き → WordPress投稿フロー

CLAUDE.mdの共通制約（draft必須・写真バイナリ非送信・アップロード前確認・本文2,500字以内）を前提とする。

## 入力

以下のいずれか:

- reve-writerの引き渡しブロック（複数記事の場合は記事ごとに1ブロック）:

```
【Claude Codeへの引き渡し】
Notionページ URL: https://www.notion.so/{ページURL}
スラッグ: {スラッグ}
記事タイプ: {Type A / B / C / D / E}
```

- ページ名の指定（例: `2026-06-04_event-makerfaire-tokyo-2026`）または「最新の下書き」

## STEP 1: Notion下書きページの取得

- 取得は必ず `notion-fetch` でURLを直接指定する。**`notion-search` は使用禁止**（全文検索になり低速のため）
- URLは引き渡しブロックの `Notionページ URL:` から読み取る
- 対象はステータス = "下書き生成済み" のページ

## STEP 2: メタ情報と本文の分離

`---` より前のメタ情報ブロックと本文を**必ず分離**する。メタ情報は本文（contentパラメータ）に絶対に含めない。

| メタフィールド | 用途 |
|---|---|
| ステータス | 処理フラグのみ（投稿しない） |
| 記事タイプ | テンプレート選択に使用 |
| スラッグ | `slug` パラメータ |
| カテゴリ | `categories` パラメータ |
| メタディスクリプション | `meta.the_page_meta_description` |
| NAS写真フォルダ | 写真マッチングに使用 |
| 選定写真リスト | 写真マッチングに使用（id・url込みの場合は再アップロード不要） |

## STEP 3: 記事タイプ判定とテンプレート選択

メタ情報の `記事タイプ:` を読み取り、[templates/types.html](templates/types.html) から該当タイプのセクションを使う。読み取れない場合はユーザーに確認してから進む。

| 記事タイプ | types.html内のセクション | 対応DB |
|---|---|---|
| Type A/B/C | 聖地巡礼記事（共通ベース） | Visits DB |
| Type D | イベントレポート | Events DB |
| Type E | お出かけレポート | Events DB |

テンプレートの `{{...}}` はNotionデータで置換する。データ不足時は★マーカー（`[★要加筆: ...]` 等、CLAUDE.md参照）を挿入する。

## STEP 4: 写真マッチング（フロー選択）

NAS写真フォルダを `ls` で確認後、以下の優先順でフローを選択:

| 条件 | フロー |
|---|---|
| 選定写真リストが記入済み（`id:...` 付き） | アップロード不要 → STEP 6の埋め込みのみ |
| 選定写真リストが記入済み（ファイル名のみ） | アップロードのみ実行（STEP 5へ） |
| `_manifest.json` がフォルダ内に存在 | `image-selector` エージェントで写真選定 |
| それ以外 | ファイル名マッチング（聖地巡礼: ファイル名に聖地スポットDBの `{スラッグ}` を含むファイル / イベント: リスト照合、リスト空なら全ファイル提示） |

ファイル命名規則は `YYYYMMDD-{slug}-{NNNN}.jpg`（詳細は `CLAUDE.local.md`）。
例: スラッグ `numazu-mito-house` → `20240503-numazu-mito-house-0001.jpg` がマッチ。

`_manifest.json` がなく事前索引したい場合は `/index-photos` スキルを参照。
フォルダが存在しない・空の場合は `[★写真: フォルダが見つかりません（パス確認が必要）]` を挿入して続行。

## STEP 5: フェーズ1 — 並列実行

**photo-uploader** と **proofreader** を全記事分まとめて同時起動する（直列処理は禁止）。

```
オーケストレーター（Claude Code本体）
  ├── photo-uploader（記事A） ─┐
  ├── photo-uploader（記事B） ─┤ 全部並列
  ├── proofreader（記事A）   ─┤
  └── proofreader（記事B）   ─┘
```

photo-uploaderへの指示:

```
以下を実行せよ:
- NAS写真フォルダ: {フォルダパス}
- 選定写真リスト: {ファイル名リスト}
上記フォルダの写真をWordPress Media APIに並列アップロードし、
取得したid・url（media_details.sizes.large.source_url。なければsource_urlにフォールバック）を一覧で返せ。
バイナリデータをClaude APIに送らないこと。
```

proofreaderへの指示:

```
以下の観点で下書きをチェックし、修正案を箇条書きで返せ:
1. 文体がCLAUDE.mdのスタイルガイドに準拠しているか
2. ★マーカーが残っていないか
3. 文字数が2,000〜2,500文字の範囲内か
4. 数字・固有名詞に誤りがないか
修正が必要な場合は該当箇所と修正案をセットで示せ。
```

画像POSTのみ403になる場合はConoHa WING側WAFの誤検知の可能性 →
`docs/design/wp-post-troubleshooting.md` の「4. 画像アップロードのみ403になる」を参照。

## STEP 6: ユーザー確認（1回のみ）

全記事のマッチング結果・校正結果をまとめて**1回**表示してから承認を受ける。承認なしにwp-posterを実行しない。

単一記事:

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

複数記事:

```
【並列投稿 確認】3記事の準備ができました

記事A: 【イベントレポート】Maker Faire Tokyo 2026...  🖼 5枚  ✅ 校正OK  ✅ 2,340字
記事B: 【お出かけ】神津島レポート...                  🖼 4枚  ✅ 校正OK  ⚠️ 2,610字（上限超過）
記事C: ラブライブ! 聖地巡礼 沼津編...                🖼 6枚  ✅ 校正OK  ✅ 2,180字

投稿してよければ「OK」、修正がある場合は記事名と指示を。
```

## STEP 7: フェーズ2 — wp-poster（承認後のみ）

アップロード結果の `id`・`url` をGutenbergブロックの `{{photo_id}}`・`{{photo_url}}` に埋め込み、
**wp-poster** エージェントで投稿する（技術仕様・PowerShellコードは `.claude/agents/wp-poster.md` が正）。
一部の写真アップロードが失敗した場合は該当箇所に `[★写真: アップロード失敗]` を挿入する。

wp-posterへの指示:

```
ユーザーの承認後に以下を実行せよ:
1. photo-uploaderが返したid・urlをGutenbergブロックの{{photo_id}}・{{photo_url}}に埋め込む
2. WP REST APIで下書き投稿（status: draft）
3. Notionの下書きページのステータスを「投稿済み」に更新
4. 編集URLを表示
```

### 投稿パラメータ

| 記事タイプ | title | slug |
|---|---|---|
| Type A/B/C | `{{series}} 聖地巡礼 {{location}}編（{{year}}年{{season}}）` | `{location}-pilgrimage-{year}-{season}` |
| Type D | `【イベントレポート】{{event_name}}に行ってきた（{{year}}年）` | `event-{english-event-name}-{year}` |
| Type E | `【お出かけ】{{destination}} {{activity}}レポート（{{year}}年）` | `visit-{english-destination}-{year}` |

```json
{
  "title": "{{title}}",
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

- メタディスクリプション: 120文字以内。「場所/イベント名 + 何が見られるか + 一言感想」を含める
- 聖地巡礼記事は `categories`/`tags`/`meta` を省略した最小パラメータでもよい（CLAUDE.md参照）

## STEP 8: 後処理

1. Notionの下書きページのステータスを "投稿済み" に更新
2. 「下書き投稿しました: [編集URL]」と表示（複数記事は `✅ 記事A → {編集URL}` 形式で列挙）
3. **聖地巡礼のみ:**
   - 来訪記録DB の Status を "Writing" に更新し、Article URL を記録
   - 使用ファイル名を Visits DB の `選定写真リスト` に書き戻す（次回の再マッチング省略のため）
   - シリーズ記事はナビカード用メニューに記事を追加し、記事末尾に `[navi_list name="メニュー名"]` があることを確認
