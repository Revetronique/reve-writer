# Revetroniqueブログ 記事自動生成システム 設計書（完全版）

---

## 1. プロジェクト概要

### 目的
ブログの記事作成を効率化する。
ラブライブ聖地巡礼記事を主軸に、技術チュートリアル・DIY等にも対応する。

### 要件
- テーマと箇条書きメモから記事の下書きを自動生成
- NAS上の写真・動画を記事に自動で紐づけ
- スマホから現地でデータ入力できる
- 写真データをクラウドに送らずローカルに保持
- パーマリンク変更時のリンク切れを自動防止
- シリーズ記事の目次を自動管理
- WordPressのブロックエディタで手動編集も可能

### 技術スタック
- データベース: Notion
- エンジン: Claude Code（ローカルPC上で動作）
- CMS: WordPress + Cocoonテーマ
- 接続: Notion MCP / WordPress MCP（claudeus-wp-mcp）
- メディア: Synology NAS（SMBマウント、LAN内アクセス）
- カスタムコード: 不要（Notion + Claude Code + MCP で完結）

---

## 2. システム構成

```
┌──────────────────────────────────────────────┐
│  入力端末                                      │
│  ├── Smartphone（Notionアプリ、現地でメモ入力） │
│  └── PC browser（Notion Web、帰宅後の補完）    │
└──────────────┬───────────────────────────────┘
               ▼
┌──────────────────────────────────────────────┐
│  Notion（データベース + スタイルルール）         │
│  ├── Series DB        作品マスター             │
│  ├── Spots DB         スポットマスター          │
│  ├── Appearances DB   登場情報（話数/MV等）     │
│  ├── Visits DB        巡礼ログ                 │
│  └── Writing Style    文章スタイルルール（ページ）│
└──────────────┬───────────────────────────────┘
               │ Notion MCP（OAuth認証）
               ▼
┌──────────────────────────────────────────────┐
│  Claude Code（ローカルPC上で動作）              │
│  ├── CLAUDE.md       = オーケストレーター       │
│  ├── Notion MCP      → DB読み書き              │
│  ├── NAS (SMB)       → 写真ファイル名取得       │
│  ├── Claude API      → 文章生成（テキストのみ）  │
│  └── curl            → WP写真アップロード       │
└──────────────┬───────────────────────────────┘
               │ REST API（PC → WordPress 直接通信）
               ▼
┌──────────────────────────────────────────────┐
│  WordPress（$env:WP_SITE_URL）                 │
│  ├── Cocoonテーマ + Gutenbergブロックパターン   │
│  ├── Redirectionプラグイン（パーマリンク監視）   │
│  └── ナビカード（シリーズ記事の目次）            │
└──────────────────────────────────────────────┘
```

### 役割分担

| レイヤー | 役割 | 保存場所 |
|---------|------|---------|
| データベース | 作品・スポット・登場情報・訪問ログ | Notion |
| 文章スタイル | トーン・構成ルール | Notion（Writing Styleページ） |
| HTMLテンプレート | Gutenbergブロック記法 | CLAUDE.md |
| オーケストレーション | データ取得→生成→投稿 | Claude Code + CLAUDE.md |
| 写真・動画 | メディアファイル | Synology NAS（LAN内SMB） |
| 記事の見た目 | CSS・装飾・レイアウト | WordPress / Cocoon |
| リダイレクト | 旧URL→新URLの自動転送 | Redirectionプラグイン |
| シリーズ目次 | 記事一覧のカード表示 | Cocoonナビカード |

### データの流れとプライバシー境界

| データ | 経路 | クラウド経由 |
|--------|------|-------------|
| スポット情報・メモ | Notion ↔ Claude Code | あり（テキスト） |
| 写真ファイル名一覧 | NAS → Claude Code | なし（LAN内） |
| 写真バイナリ | NAS → PC → WordPress | なし（curl直接） |
| 記事HTML | Claude Code → WordPress | あり（テキスト） |
| AI生成テキスト | Claude Code → Claude API | あり（テキスト） |

**写真・動画のバイナリデータはローカルネットワーク外に出ない。**

---

## 3. Notion データベース設計

### 3-1. Series DB（作品マスター）

| プロパティ | 型 | 例 |
|-----------|----|----|
| Name | Title | ラブライブ!サンシャイン!! |
| Short name | Text | サンシャイン |
| Franchise | Select | ラブライブ! |
| Official URL | URL | https://www.lovelive-anime.jp/uranohoshi/ |

### 3-2. Spots DB（スポットマスター）

| プロパティ | 型 | 例 |
|-----------|----|----|
| Name | Title | 内浦海岸 |
| Series | Relation → Series | サンシャイン |
| Region | Text | 沼津市 |
| Address | Text | 静岡県沼津市内浦 |
| Tips | Text | 朝が空いてておすすめ |
| Photo keywords | Text | 内浦,海岸,海 |
| Latitude | Number | 35.012345 |
| Longitude | Number | 138.876543 |
| Status | Select | 訪問済 / 未訪問 |

**座標の仕様:**
- 形式: WGS84 10進法（Decimal Degrees）
- 精度: 小数点以下6桁（約11cm精度、スポット特定に十分）
- 入力方法: Google Mapsで右クリック → 座標コピー → Notionに貼付
- スマホ: Googleマップアプリで長押し → 座標タップでコピー
- 注意: 日本測地系の座標をそのまま入れると約450mずれる。
  Google Maps取得値なら問題なし

Notionのビュー設定:
- Table view: 一覧・編集用
- Gallery view: スポット写真をカード表示
- Board view: Statusでグループ化（訪問済/未訪問）

### 3-3. Appearances DB（登場情報）

Spots DBからEpisodeフィールドを分離。
1つのスポットが複数話・MV・劇場版に登場するケースに対応。
1つの登場 = 1レコード。

| プロパティ | 型 | 例 |
|-----------|----|----|
| Label | Title | 内浦海岸 × 1期 第1話 |
| Spot | Relation → Spots | 内浦海岸 |
| Series | Relation → Series | サンシャイン |
| Source type | Select | TVアニメ / 劇場版 / MV / ゲーム / CM |
| Source detail | Text | 1期 第1話「輝きたい!!」 |
| Scene | Text | 千歌が海岸を走るシーン |
| Timestamp | Text | 12:34頃 |

例: 内浦海岸のAppearancesレコード
- 内浦海岸 × 1期OP（MV /「青空Jumping Heart」）
- 内浦海岸 × 1期 第1話（TVアニメ / 千歌が走るシーン）
- 内浦海岸 × 2期 第13話（TVアニメ / 最終話の集合シーン）
- 内浦海岸 × 劇場版（劇場版 / 冒頭の回想）
- 内浦海岸 × Aqours MV（MV /「HAPPY PARTY TRAIN」）

### 3-4. Visits DB（巡礼ログ）

| プロパティ | 型 | 例 |
|-----------|----|----|
| Title | Title | 沼津聖地巡礼 2026春 |
| Series | Relation → Series | サンシャイン |
| Visited spots | Relation → Spots | 内浦海岸, 松月 |
| Visit date | Date | 2026-04-15 |
| Weather | Select | 晴れ |
| Budget | Text | 約15,000円 |
| 写真フォルダ | Text | Pilgrimage\sunshine\numazu\2026-04\ |
| 選定写真リスト | Text | spot-uchi-harbor-01.jpg(id:1234\|url:https://...) |
| Memo | Text | 箇条書きメモ |
| Series tag | Text | 沼津2026春（ナビカード用） |
| Status | Select | Draft / Writing / Published |
| Article URL | URL | （公開後に記入） |

Memoの書き方（スマホから現地で入力）:
```
- 内浦海岸でOPの景色を見た
- マリンパークでペンギンと撮影
- 沼津バーガーのみかんバーガーが美味しかった
- 松月でみかんどら焼き購入（250円）
```

### 3-5. Events DB（イベント・お出かけ）

| プロパティ | 型 | 説明 |
|-----------|----|----|
| イベント名 | Title | 正式名称 |
| 日付 | Date | 開催日 |
| 場所 | Text | 会場名＋住所 |
| 座標 | Text | WGS84 小数6桁 |
| カテゴリ | Select | イベントレポート / お出かけレポート / ライブレポート |
| 記事タイプ | Select | Type D / Type E |
| ステータス | Select | 予定 / メモ収集中 / 素材整理中 / 素材整理完了 / 執筆中 / レビュー待ち / 公開済み |
| 記事URL | URL | 公開後に記入 |
| 写真フォルダ | Text | NASパス（例: Event\2026-06-makerfaire\） |
| 写真選定リスト | Text | 使用ファイル名カンマ区切り |
| メモ | Text | 現地メモ + 帰宅後補完 |
| 見出し構成 | Text | H2/H3の箇条書き構成 |
| 公開期限 | Date | イベント日+2日が目安 |
| アフィリエイト候補 | Multi-select | Amazon / Rakuten / BOOTH / その他 |

### 3-6. 下書きDB（下書き置き場）

reve-writer（Claude.ai）が生成した記事をNotionページとして保存する場所。
Claude Codeがここを取得してWordPressに投稿する。

**ページタイトル形式:** `YYYY-MM-DD_{スラッグ}`（例: `2026-06-04_event-makerfaire-tokyo-2026`）

各ページの冒頭（`---` より前）にメタ情報を記載:
```
ステータス: 下書き生成済み
記事タイプ: Type D
スラッグ: event-makerfaire-tokyo-2026
カテゴリ: イベントレポート
メタディスクリプション: （120文字以内）
NAS写真フォルダ: Event\2026-06-makerfaire\
選定写真リスト: makerfaire-venue-01.jpg(id:1234|url:https://...), makerfaire-keyboard-01.jpg(id:1235|url:https://...)
---
（ここより後のみが本文）
```

ステータスの遷移:
- `下書き生成済み` → reve-writerが書き込んだ直後
- `投稿済み` → Claude CodeがWordPressにPOSTした後に更新

### 3-7. Writing Style（ページ）

DBではなく通常のNotionページ。Claude Codeが参照する文章ルール。

```
# 基本スタイル
- 挨拶: どうも、Reveです。
- 締め: もし参考になれば幸いです。
- 見出し: 【】で囲む
- 一人称: 当方（または省略）
- 読者: 皆さん
- トーン: 会話調、謙虚、実用重視
- 感情表現: (汗)、ｗ を適度に使用

# 聖地巡礼記事の構成
1. 挨拶 + 動機
2. 【今回の聖地巡礼について】概要テーブル
3. 【スポット名】× N — 各スポットの紹介
4. 【グルメ・お土産】（あれば）
5. 【まとめ】感想 + 次回予告
6. 【参考・アクセス情報】

# 技術チュートリアルの構成
1. 挨拶 + 動機
2. 【前提条件】
3. 【実装方法】コード + 解説
4. 【注意点】
5. 【まとめ】

# 写真の挿入ルール
- 各スポットに1〜3枚
- キャプション付き
- NASのパスからファイル名で対応
```

---

## 4. WordPress 設定

### 4-1. パーマリンク構造

**`/%postname%/`（投稿名のみ）を使用。**

カテゴリをURLに含めない。カテゴリ変更・タグ変更時にURLが変わらない。
スラッグは英語のケバブケースで手動設定。

スラッグ命名規則:
- 聖地巡礼: `{location}-pilgrimage-{year}-{season}`
  例: `numazu-pilgrimage-2026-spring`
- 技術記事: `{topic-keyword}`
  例: `unity-quaternion-rotation`
- DIY: `diy-{project-name}`
  例: `diy-led-matrix-controller`

### 4-2. Redirectionプラグイン

- インストール: 管理画面 → プラグイン → 新規追加 → 「Redirection」
- 設定: 「WordPressの投稿と固定ページのパーマリンクの変更を監視」をON
- 効果: スラッグを変更した瞬間に旧URL→新URLの301リダイレクトが自動作成
- ログ: すべてのリダイレクトと404エラーを記録

### 4-3. ブロックパターン（非同期）

WordPress管理画面でテンプレートを組み、非同期パターンとして保存。
挿入後は独立したブロックになり、記事ごとに自由に編集可能。
（同期パターンは編集すると全記事に反映されるため使わない）

作り方:
1. 新規投稿で聖地巡礼記事の構成をブロックで組む
2. 全ブロック選択 → ⋮ → 「パターンを作成」
3. 「同期」をオフに → 保存

使い方:
1. 新規投稿 → ＋ → パターンタブ → テンプレートを選択
2. 中身を書き換えて記事を完成

CLAUDE.mdへの転記:
1. パターンを挿入した投稿を「HTMLとして編集」モードで開く
2. Gutenbergブロック記法をコピー
3. CLAUDE.mdに貼り付け
→ 手動投稿でもClaude Code投稿でも同じ見た目になる

### 4-4. Gutenbergブロックテンプレート（CLAUDE.mdに記載）

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

<!-- スポット（繰り返し） -->
<!-- wp:heading -->
<h2 class="wp-block-heading">【{{spot_name}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>（{{series}} {{episode}}）</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{spot_description}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{photo_url}}" alt="{{spot_name}}"/>
<figcaption class="wp-element-caption">{{caption}}</figcaption>
</figure>
<!-- /wp:image -->

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
```

### 4-5. シリーズ記事の目次（ナビカード）

複数記事に分けた巡礼旅行の一覧表示にCocoonのナビカードを使用。

セットアップ:
1. 管理画面 → 外観 → メニュー → 新規メニュー作成（例:「沼津巡礼シリーズ」）
2. メニュー項目にシリーズの各記事を順番に追加
3. 記事内に `[navi_list name="沼津巡礼シリーズ"]` を挿入

Claude Code連携:
- 記事投稿時に自動でナビカード用メニューに記事を追加
- 各記事の末尾にナビカードのショートコードを埋め込み
- Visits DBの Series tag（例:「沼津2026春」）で同シリーズを判定

応用:
- まとめ固定ページ + ナビカード: Day別にナビカードを分けて配置
- new_list ショートコード: 共通タグで自動一覧（順番制御は不可）

---

## 5. 写真・動画の管理

### NASアクセス方式

**SMBマウント（LAN内）を使用。QuickConnectは写真以外の用途で残してもよい。**

```bash
# macOS
mount_smbfs //user@NAS_IP/photos /mnt/nas/photos

# Linux
mount -t cifs //NAS_IP/photos /mnt/nas/photos -o username=user

# Windows
net use Z: \\NAS_IP\photos /user:user
```

### フォルダ構成

NASマウントポイントは `\\DiskStation\Photos`（Windows: `Y:\`、macOS: `/Volumes/Photos`）。

```
\\DiskStation\Photos\
├── Event\                             ← 美術館・展示会・イベント・お出かけ等
│   ├── 2026-06-makerfaire\
│   └── 2026-07-kozushima\
├── Travel\                            ← 旅行写真（命名規則なし、既存のまま）
│   └── {YYYY-MM-目的地}\
└── Pilgrimage\                        ← 聖地巡礼写真（予定）
    └── {作品名}\
        └── {場所名}\
            └── {YYYY-MM}\
```

**ファイル命名規則:**

| 種別 | パターン | 例 |
|------|----------|----|
| 聖地巡礼 | `spot-{スラッグ}-{連番2桁}.jpg` | `spot-uchi-harbor-01.jpg` |
| イベント・お出かけ | `{任意説明}-{連番2桁}.jpg` | `makerfaire-keyboard-01.jpg` |

- 拡張子は小文字（`.jpg` / `.png`）
- 区切り文字はハイフンのみ（アンダースコア不使用）

### 写真マッチングの仕組み

Claude Codeがやること:
1. NASフォルダのファイル名一覧を取得（`ls` コマンド、LAN内）
2. Visits DBのMemoキーワード / Spots DBのPhoto keywordsとファイル名を文字列比較
3. マッチ結果をユーザーに確認表示
4. **画像のバイナリデータはClaude APIに送信しない**

### WordPressへの写真アップロード

PowerShell Jobsで全ファイルを**並列アップロード**（PC → WordPress、クラウド不経由）。

```powershell
$nasFolder = "Y:\Event\2026-06-makerfaire\"
$files = @("makerfaire-venue-01.jpg", "makerfaire-keyboard-01.jpg")

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
```

取得した `id` と `source_url` をGutenbergブロックの `{{photo_id}}` / `{{photo_url}}` に埋め込む。

**アップロード前にユーザー確認を必ず挟む。**

---

## 6. MCP接続

### Notion MCP（公式）

```bash
claude mcp add --transport http notion https://mcp.notion.com/mcp
# 初回: /mcp → Notion選択 → ブラウザでOAuth認証
```

### WordPress MCP（claudeus-wp-mcp）

認証情報をファイルに残さないラッパースクリプト経由で起動。

```bash
claude mcp add claudeus-wp-mcp -- ./start-wp-mcp.sh
```

start-wp-mcp.sh:
1. `.env` から WP_USERNAME / WP_APP_PASSWORD を読み込み
2. 一時ファイルに wp-sites.json を生成（chmod 600）
3. `WP_SITES_PATH=一時ファイル npx -y claudeus-wp-mcp` で起動
4. 終了時に `trap` で一時ファイル削除

### 認証情報の管理

`.env` ファイルで一元管理。config.yamlにはパスワードを書かない。

```env
SYNOLOGY_QUICKCONNECT_ID=...    # NAS（QuickConnect使用時のみ）
SYNOLOGY_USERNAME=...
SYNOLOGY_PASSWORD=...
WP_SITE_URL=https://your-blog-domain.example.com
WP_USERNAME=...
WP_APP_PASSWORD=...
ANTHROPIC_API_KEY=...
```

`.env` / `wp-sites.json` は `.gitignore` に記載。

---

## 7. 著作権の注意点

### 使えるもの（リスクが低い）
- 自分で撮影した現地の写真・動画（聖地巡礼ブログの主力）
- 公式サイトへのリンク（URLのみ、画像埋め込みはしない）
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
- 特にサンライズは二次創作に厳しい傾向

### アフィリエイト
- 旅行系（じゃらん、楽天トラベル等）やAmazon関連商品は問題になりにくい
- 自分の写真メイン + 文章で説明の構成なら、公式素材の使用問題と分離できる
- アフィリエイトがあると営利目的とみなされやすいため、引用要件をより厳密に

---

## 8. CLAUDE.md（Claude Code設定ファイル）

CLAUDE.mdはプロジェクトルートに配置し、以下の主要セクションで構成される。
最新の内容は実際の `CLAUDE.md` を参照のこと（このドキュメントはサマリー）。

### 主要セクション構成

| セクション | 内容 |
|-----------|------|
| 概要 | システム説明・方針 |
| Notion DB構成 | 全DB定義・下書きページ構造・ステータス遷移 |
| 記事タイプ一覧 | Type A〜E の用途・DB・テンプレート対応 |
| 共通制約 | draft投稿・写真バイナリ非送信・ユーザー確認必須 |
| 文章スタイル | スタイルルール・プレースホルダー定義 |
| 記事タイプ別ルール | Type A/B/C/D/E 固有ルール |
| Notion取得ルール | notion-fetch 使用、notion-search 禁止 |
| 引き渡しブロック形式 | reve-writer → Claude Code の連携フォーマット |
| 複数記事の並列処理 | オーケストレーター構成（フェーズ1/2） |
| 記事生成フロー | Type A/B/C と Type D/E の各フロー |
| 写真マッチングフロー | STEP 1〜5 |
| NAS | マウント方法・フォルダ構造・命名規則 |
| パーマリンク | /%postname%/ ・スラッグ命名規則 |
| WordPress投稿パラメータ | 記事タイプ別JSONフォーマット |
| サブエージェント構成 | photo-uploader / proofreader / wp-poster |
| Gutenbergブロックテンプレート | Type A/B/C・Type D・Type E |

### ローカル設定

環境固有の値（Notionページ URL 等）は `CLAUDE.local.md`（Git管理外）に記載。

---

## 9. 運用フロー

### Phase 1: 現地（スマホ）

1. Notionアプリで Visits DB を開く
2. 新規エントリ追加（タイトル、Series、Visit date、Weather）
3. Memo に箇条書きでメモ入力
4. Visited spots にスポットをリレーション追加
5. 新しいスポットがあれば Spots DB に新規追加
   （Google Mapsから座標コピー → Latitude/Longitude に貼付）
6. 新しい登場情報があれば Appearances DB に追加

### Phase 2: 帰宅後の準備

1. NASに写真を保存（`Event\` / `Pilgrimage\` フォルダ）
2. Visits DB / Events DB の `写真フォルダ` にパスを記入
3. Visits DB の Status を "Draft" に、Events DB のステータスを "素材整理完了" に設定

### Phase 2.5: reve-writer（Claude.ai）で下書き生成

1. reve-writerにメモを渡す
2. 不足確認（1回）→ 見出し構成＋下書きを生成
3. 承認後、Notionの「下書き」ページに自動保存
4. reve-writerが引き渡しブロックを出力:
   ```
   【Claude Codeへの引き渡し】
   Notionページ URL: https://www.notion.so/...
   スラッグ: event-makerfaire-tokyo-2026
   記事タイプ: Type D
   ```

### Phase 3: 投稿（Claude Code）

引き渡しブロックをClaude Codeに貼り付けると自動実行:

1. `notion-fetch` でNotionページ取得
2. メタ情報と本文を `---` で分離
3. **フェーズ1（並列）**: photo-uploader + proofreader を同時起動
4. 確認画面を1回表示（写真マッチング結果 + 校正結果）
5. **フェーズ2（承認後）**: wp-poster でWordPress下書き投稿
6. Notionのステータスを "投稿済み" に更新
7. 「下書き投稿しました: [編集URL]」

### Phase 4: 確認・公開

1. WordPress管理画面で下書きを確認
2. ブロックエディタで微調整（見出し・写真の並び・キャプション等）
3. パーマリンク（スラッグ）を確認
4. 公開
5. Visits DB の Status → "Published"、Article URL 記入

---

## 10. 初期セットアップ手順

### Step 1: Notion

1. Notion アカウント作成（無料プラン）
2. ワークスペースに「聖地巡礼」ページを作成
3. Series / Spots / Appearances / Visits の各DBを作成
4. Writing Style ページを作成
5. サンプルデータを入力（サンシャイン沼津など）

### Step 2: WordPress

1. Redirectionプラグインをインストール・有効化
2. パーマリンク変更監視をONに設定
3. パーマリンク構造を /%postname%/ に設定
4. アプリケーションパスワードを生成（ユーザー → プロフィール）
5. ブロックパターン（非同期）を作成・保存
6. ナビカード用メニューの作成

### Step 3: Claude Code

1. Notion MCP を接続
   `claude mcp add --transport http notion https://mcp.notion.com/mcp`
2. WordPress MCP を接続
   `claude mcp add claudeus-wp-mcp -- ./start-wp-mcp.sh`
3. `.env` ファイルに認証情報を記入
4. `CLAUDE.md` を作成（Gutenbergテンプレートを含む）
5. 接続テスト: `> Notion の Series DB を見せて`
6. 生成テスト: `> テストで沼津の聖地巡礼記事を生成して（dry run）`

### Step 4: NAS

1. DSM → コントロールパネル → ファイルサービス → SMB を有効化
2. PC からネットワークドライブとしてマウント
3. 写真のフォルダ構成を整理（作品名/イベント名）

---

## 11. 将来の拡張

### 聖地巡礼以外の記事タイプ
- Writing Style ページに記事タイプごとのスタイルを追加
- CLAUDE.md にGutenbergテンプレートを追加
- Notion DB はそのまま活用可能

### X (Twitter) 連携
- 記事公開後にXへの告知を自動化
- X MCP または IFTTT/Zapier でWordPress公開をトリガー

### Google Maps埋め込み
- Spots DB の座標から Google Maps 埋め込みURLを自動生成
- 記事内にスポットの地図を表示

### 写真のExif活用
- スマホで撮った写真のGPS情報からSpots DBの座標を自動入力
- 撮影日時からVisits DBの訪問日を補完

### 独自ドメイン移行
- 聖地巡礼コンテンツが十分な規模になったら、
  専用ドメインへの移行を検討
- Redirectionプラグインで旧URL→新ドメインへの301転送

---

## 12. ファイル構成

```
blog/
├── CLAUDE.md                  # Claude Code 設定（中核）
├── CLAUDE.local.md            # ローカル設定（git管理外）
├── CLAUDE.local.md.example    # ローカル設定テンプレート
├── .gitignore
└── docs/
    ├── design/
    │   ├── reve-writer-design.md      # 本ドキュメント（システム設計書）
    │   └── wp-post-troubleshooting.md # WP REST API投稿トラブルシュート
    └── prompts/
        ├── reve-writer-system-prompt.md  # reve-writer（Claude.ai）用システムプロンプト
        └── claude-md-event-module.md     # イベント記事モジュール（CLAUDE.mdに統合済み）
```

**Pythonコード・シェルスクリプト不要。** テンプレート・DB・オーケストレーション全て
Notion + CLAUDE.md + MCP で完結。認証情報は Claude Code の `settings.local.json` の `env` に設定。
