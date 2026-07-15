# reve-writer セットアップ状況

記事生成パイプライン（Notion → Claude Code → WordPress。CLAUDE.md と `.claude/skills/` に定義）を動作させるための準備状況をまとめたドキュメント。

---

## 設定済み ✅

### 1. Notion MCP

**ファイル:** `.mcp.json`（プロジェクトルート、Git管理外）

`.mcp.json.example` をコピーして `.mcp.json` を作成し、`ntn_YOUR_NOTION_INTEGRATION_TOKEN` を実際のトークンに置き換える。

```bash
cp .mcp.json.example .mcp.json
# または Windows
copy .mcp.json.example .mcp.json
```

**Windows での `npx` が見つからないエラーが出た場合:**
`.mcp.json` の `command` と `args` を以下に変更する（`npx` の代わりに `cmd /c npx` を使う）:

```json
"command": "cmd",
"args": ["/c", "npx", "-y", "@notionhq/notion-mcp-server"]
```

- インテグレーション名: `reve-writer`（Notionの「接続」から各DBに追加済み）
- 利用可能ツール: `mcp__notion__API-*`（検索・ページ取得・プロパティ更新等）
- **注意:** Claude Code起動時に `.claude/settings.local.json` の `enabledMcpjsonServers: ["notion"]` が必要

---

### 2. WordPress 認証情報

**ファイル:** `.claude/settings.local.json`（gitignore対象）

```json
{
  "env": {
    "WP_SITE_URL": "https://your-blog-domain.example.com",
    "WP_USERNAME": "your-wp-username",
    "WP_APP_PASSWORD": "（Application Password）"
  }
}
```

- 認証方式: Basic認証 + Application Password（WP管理画面で発行）
- 動作確認: `/wp-json/wp/v2/users/me` でユーザーID:1が返ることを確認済み

---

### 3. WordPress 投稿方式の確立

**動作確認済みの投稿コード** → `wp-post-troubleshooting.md` 参照

- `Invoke-RestMethod` ではなく `curl.exe` を使用
- HTMLファイルは `[System.IO.File]::ReadAllText` で読み込む（`Get-Content -Raw` は不可）
- JSONはBOMなしUTF-8で書き出す（`[System.Text.UTF8Encoding]::new($false)`）
- 実績: 投稿ID:XXXX（イベントレポート記事）で下書き投稿成功

---

### 4. NAS アクセス（写真付き記事に対応）

**マウント状態:** ✅ `Y:\`（Windows ネットワークドライブ）

**セットアップ:**
```powershell
# Synology DiskStation Photos 共有をマウント
net use Y: \\DiskStation\Photos /user:USERNAME PASSWORD /persistent:yes
```

**フォルダ構成:**

トップレベルは `LoveLive\`（グループ別）、`Travel\`（国・地域別）、`Event\`（イベント名別）、`Dining\` の4分類。
**詳細なフォルダ構成・命名規則は `CLAUDE.local.md`（Git管理外）を参照**（環境固有のためここには転記しない）。

**写真命名規則:** `YYYYMMDD-{slug}-{NNNN}.jpg`
（例: `20240503-numazu-0001.jpg`、`20260601-makerfaire-tokyo-2026-0001.jpg`。
リネームは `/rename-photos` スキル → `.claude/scripts/rename-photos.sh` で実行）

**Notion連携:**
- Visits DB / Events DB の「写真フォルダ」フィールドに NAS パスを記入
- 「選定写真リスト」フィールドにアップロード対象ファイルを記入（カンマ区切り）

**注意:** バイナリデータは Claude API を経由しない（PC → WordPress 直接）

**取り込みフロー:**
```
[スマホ/カメラ] → [NAS所定フォルダへ手動コピー]
                         ↓
               [HEIC→JPEG変換、元HEICは残す]
                         ↓
               [EXIF日付＋slug指定でリネーム]
                         ↓
               image_indexer.py 実行
               （manifest.json生成）
```

---

### 5. reve-writer（Claude.ai用プロジェクト指示 + Notion接続）

**ファイル:** `docs/prompts/reve-writer-system-prompt.md`

このファイルを **claude.ai のプロジェクト指示** に設定し、**Notionコネクタを接続**することで、
Claude.ai が Notion メモから記事下書きを自動生成し、Notion に保存できるようになります。

#### 5-A. プロジェクト指示の設定

1. `docs/prompts/reve-writer-system-prompt.md` を開く
2. 全文をコピー（`Ctrl+A` → `Ctrl+C`）
3. [claude.ai](https://claude.ai) にアクセス
4. プロジェクト名「reve-writer」を作成（または既存のプロジェクトを開く）
5. プロジェクト設定 → 「Instructions」 に貼り付けて保存

#### 5-B. Notion コネクタの接続（claude.ai ブラウザ版）

claude.ai の **Integrations（統合）** 機能を使ってNotionを接続する。

1. [claude.ai](https://claude.ai) → プロジェクト「reve-writer」を開く
2. 左サイドバーまたはプロジェクト設定の **「Add integrations」** をクリック
3. 一覧から **Notion** を選択
4. 「Connect」をクリック → Notionの認証画面にリダイレクト
5. Notionにログインし、接続するワークスペースを選択
6. **アクセスを許可するページ/DBを選択:**
   - 「下書き」親ページ（`CLAUDE.local.md` に記載のURL）
   - Events DB
   - Visits DB（聖地巡礼記事を生成する場合）
7. 「Allow access」で承認 → claude.ai に戻り接続完了を確認

> **注意:** Notionコネクタは claude.ai の有料プラン（Pro以上）が必要。
> 接続後は会話内で「Notionに保存して」と指示するだけで書き込みが実行される。

#### 5-C. Notion コネクタの接続（Claude デスクトップ版）— 任意

> **claude.aiブラウザ版とデスクトップ版の設定は共有されない。**
> 両者はアーキテクチャが異なり（ブラウザ版はAnthropicサーバー経由のOAuth、デスクトップ版はローカルMCPサーバー）、
> それぞれ独立した設定が必要になる。
>
> **reve-writerの用途（メモ → Notion保存）はブラウザ版だけで完結する。**
> デスクトップ版Claudeからもreve-writerを使いたい場合のみ、以下を追加で設定する。

デスクトップ版では **MCP（Model Context Protocol）** でNotionを接続する。

1. Claude デスクトップアプリを開く
2. 設定 → **「Developer」→「Edit Config」** をクリック
   - 設定ファイルのパス: `%APPDATA%\Claude\claude_desktop_config.json`（Windows）
3. 以下を追記して保存:

```json
{
  "mcpServers": {
    "notion": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@notionhq/notion-mcp-server"],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ntn_YOUR_NOTION_INTEGRATION_TOKEN\", \"Notion-Version\": \"2022-06-28\"}"
      }
    }
  }
}
```

4. `ntn_YOUR_NOTION_INTEGRATION_TOKEN` を実際のトークンに置き換える
   - Notionインテグレーション管理画面 → 「reve-writer」インテグレーション → 「Internal Integration Secret」
5. Claude デスクトップを再起動
6. チャット入力欄の左下にツールアイコン（🔧）が表示されればMCP接続成功

> **注意:** デスクトップ版MCPはローカルPC上で動作するため、Claude Codeの `.mcp.json` とは別設定。
> 同じNotionインテグレーショントークンを使いまわして構わない。

#### Notion インテグレーションの共有設定（共通）

どちらの方法でも、接続するNotionページにインテグレーションを共有しておく必要がある。

1. Notionで「下書き」親ページを開く
2. 右上「…」→「接続」→「reve-writer」を追加
3. 同様に Events DB、Visits DB にも追加

**機能:**
- メモから記事タイプ（Type D / E）を自動判定
- 不足情報を1回にまとめて確認
- 見出し構成と下書きを同時生成
- ユーザー承認後、Notion 「下書き」ページに自動保存
- 引き渡しブロックを出力（Claude Code で投稿実行）

---

### 6. Remote Control（claude.ai連携）

**ファイル:** `.claude/settings.json`（プロジェクトローカル、git管理対象）

- `remoteControlAtStartup: true` — Claude Code起動時にRemote Controlブリッジを自動起動し、claude.aiから直接このセッションに指示を送れるようにする設定。不要な場合は `false` に変更するか、このキーを削除してよい
- `enabledMcpjsonServers: ["notion"]` — `.mcp.json` のNotion MCPサーバーを有効化
- `hooks.PreToolUse` — 禁止事項の機械的強制（2件）:
  1. `notion-search` 系ツールの呼び出しを拒否（`notion-fetch` でURL直接指定を強制）
  2. `status` に `publish` を設定するコマンドをブロック（draft必須の強制）

---

## 運用上の制約・注意事項

### SiteGuard Lite によるREST API制限

記事本文が2,500文字以内であればSiteGuard Liteの無効化は不要。
CLAUDE.mdの文字数目安（2,000〜2,500文字）を守ることで通常は回避できる。

POSTが403でブロックされた場合のデバッグ手順:
1. `Get-Content -Raw` を使っていないか確認（JSONが肥大化する原因になる）
2. 文字数が2,500文字以内か確認
3. 上記を確認してもブロックされる場合のみ WP管理画面 → SiteGuard Lite を **一時無効化** → 投稿 → **再有効化**

詳細は `wp-post-troubleshooting.md` を参照。

---

## 未対応 ❌

### WordPressカテゴリ/タグIDのマッピング

投稿パラメータの `{{category_id}}` に使う実際のIDが未確認。

確認コマンド:
```powershell
$creds = "{{WP_USERNAME}}:（APP_PASSWORD）"
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($creds))
Invoke-RestMethod -Uri "$env:WP_SITE_URL/wp-json/wp/v2/categories" `
    -Headers @{ "Authorization" = "Basic $encoded" } | Select-Object id, name, slug
```

---

## ファイル構成

```
blog/
├── CLAUDE.md                         # 常時ロードされる規則（共通制約・スタイル・スキル一覧）
├── CLAUDE.local.md                   # ローカル設定（git管理外。NotionURL・NAS構成・命名規則）
├── CLAUDE.local.md.example           # ローカル設定テンプレート
├── .mcp.json                         # Notion MCPサーバー設定（git管理外）
├── README.md                         # このファイル
├── .claude/
│   ├── settings.json                 # Remote Control・MCP有効化・PreToolUseフック
│   ├── settings.local.json           # WordPress認証情報（gitignore）
│   ├── skills/                       # ワークフロー定義
│   │   ├── post-draft/               #   Notion下書き→WP投稿（templates/types.html 含む）
│   │   ├── index-photos/             #   写真の事前索引
│   │   ├── rename-photos/            #   写真リネーム
│   │   ├── precheck/                 #   公開前チェック
│   │   └── edit-post/                #   既存投稿の修正
│   ├── agents/                       # サブエージェント定義（6本）
│   └── scripts/                      # image_indexer.py・HEIC変換・リネーム等
├── .tmp/
│   └── post-content.html             # 投稿時の一時コンテンツファイル
└── docs/
    ├── design/
    │   ├── reve-writer-design.md     # システム設計書（完全版）
    │   └── wp-post-troubleshooting.md # WordPress投稿トラブルシューティング
    └── prompts/
        ├── reve-writer-system-prompt.md  # reve-writer用システムプロンプト
        └── claude-md-event-module.md     # イベント記事仕様（アーカイブ）
```

---

## 全体アーキテクチャ

```
┌─────────────────────────────────┐
│ Phase 1: 現地でメモ入力            │
│ （スマホ・手帳など、どこでもOK）   │
└──────────────┬──────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│ Phase 2: claude.ai（reve-writer プロジェクト）       │
│ - メモを貼り付けて不足確認（1回）                    │
│ - 見出し構成＋下書き自動生成                         │
│ - Notion 下書きページに自動保存 ← ここで初めてNotion │
│ - 引き渡しブロック出力                              │
└──────────────┬──────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────┐
│ Phase 3: Claude Code（ローカル PC）                  │
│ 引き渡しブロック受信 → 複数記事対応の投稿フロー      │
│                                                     │
│ 【フェーズ1】並列実行（全記事×2エージェント）        │
│  ├─ photo-uploader: NAS写真 → WordPress            │
│  └─ proofreader: 文体チェック                      │
│                                                     │
│ 【確認画面】1回のみ表示                             │
│  ├─ 写真アップロード結果                            │
│  ├─ 校正結果                                       │
│  └─ 投稿パラメータプレビュー                        │
│                                                     │
│ 【フェーズ2】ユーザー承認後、順次実行               │
│  └─ wp-poster: WordPress REST API 投稿（draft）    │
│                                                     │
└──────────────┬──────────────────────────────────────┘
               ▼
┌──────────────────────────────────┐
│ WordPress 下書き投稿完了          │
│ 編集画面で最終確認 → 公開         │
└──────────────────────────────────┘
```

### 2 つのシステム

| システム | 環境 | 役割 | セットアップ |
|---------|------|------|-----------|
| **reve-writer** | claude.ai（ブラウザ） | メモ → 下書き生成 | docs/prompts/reve-writer-system-prompt.md を Custom Instructions に貼り付け |
| **Claude Code** | ローカル PC | 下書き → WordPress 投稿 | CLAUDE.md + MCP（Notion + WordPress） |

---

投稿ワークフローは `.claude/skills/post-draft/` に定義され、`.claude/agents/` の専門エージェントを
オーケストレーションする。複数記事は**フェーズ1を並列**、**フェーズ2を順次**実行
（フロー詳細・確認画面フォーマットは post-draft スキルを参照）。

### サブエージェント一覧（`.claude/agents/`）

| エージェント | 役割 | 実行タイミング |
|-----------|------|-------------|
| **image-indexer** | image_indexer.pyでNAS写真を解析し `_manifest.json` 生成 | フェーズ-1（任意・事前準備） |
| **image-selector** | manifest＋下書きから挿入写真を選定 | フェーズ0（任意・manifest存在時） |
| **photo-uploader** | NAS 写真 → WordPress Media API 並列アップロード | フェーズ1（並列） |
| **proofreader** | 文体・スタイルチェック（★マーカー検出） | フェーズ1（並列） |
| **wp-poster** | WordPress REST API 下書き投稿 | フェーズ2（ユーザー確認後） |
| **seo-optimizer** | タイトル・メタ・見出しのSEO分析 | 任意（依頼時のみ） |

### 記事タイプ別エージェント動作

**reve-writer（Claude.ai）:**
1. Notion メモ → 不足確認（1回） → 見出し構成＋下書き生成
2. ユーザー承認後、下書きページに自動保存
3. **引き渡しブロック出力（複数記事対応）:**
   ```
   【Claude Codeへの引き渡し】
   Notionページ URL: https://www.notion.so/...（記事A）
   スラッグ: event-makerfaire-tokyo-2026
   記事タイプ: Type D
   ---
   Notionページ URL: https://www.notion.so/...（記事B）
   スラッグ: visit-kozushima-2026
   記事タイプ: Type E
   ```

**Claude Code（オーケストレーター）:**
- 引き渡しブロックをパース（複数記事検出）
- 各記事を `notion-fetch` で取得
- photo-uploader / proofreader を**記事×2で計4エージェント**を並列起動
- 全完了を待ち、**1回の確認画面**を表示
- ユーザー承認後、wp-poster を記事ごと順次実行

---

## 動作確認済みのコマンド例

### Notionの接続確認
```
mcp__notion__API-post-search でキーワード検索 → レコードのpage_idを取得
```

### WordPress認証確認
```powershell
$creds = "{{WP_USERNAME}}:（APP_PASSWORD）"
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($creds))
Invoke-RestMethod -Uri "$env:WP_SITE_URL/wp-json/wp/v2/users/me" `
    -Headers @{ "Authorization" = "Basic $encoded" } | Select-Object id, name
```

### 複数記事の並列投稿（単一コマンド）

reve-writer から引き渡しブロック（複数記事）が返ってきたら、Claude Code に貼り付け:

```
（reve-writer の引き渡しブロック）
```

Claude Code が自動実行:
1. 2記事のメタ情報と本文を抽出
2. photo-uploader × 2 + proofreader × 2 を同時起動（4エージェント並列）
3. 5枚 + 4枚の写真が並列アップロード開始
4. 全完了後、確認画面を1回表示:
   ```
   記事A: 【イベントレポート】Maker Faire...  🖼 5枚  ✅ 校正OK  ✅ 2,340字
   記事B: 【お出かけ】神津島...               🖼 4枚  ✅ 校正OK  ✅ 2,180字
   
   投稿してよければ「OK」
   ```
5. ユーザー「OK」で wp-poster 実行（記事ごと順次）
6. 結果表示:
   ```
   ✅ 記事A → https://{WP_SITE_URL}/wp-admin/post.php?post=123&action=edit
   ✅ 記事B → https://{WP_SITE_URL}/wp-admin/post.php?post=124&action=edit
   ```

---

## 参考リソース

- **CLAUDE.md**: 常時ロードされる規則（共通制約・文章スタイル・スキル/エージェント一覧）
- **.claude/skills/**: ワークフロー定義（投稿・索引・リネーム・公開前チェック・投稿修正の各手順の真実のソース）
- **.claude/agents/**: サブエージェント実装（アップロード・投稿コードの真実のソース）
- **docs/design/reve-writer-design.md**: システムアーキテクチャ・DB設計（完全版）
- **docs/design/wp-post-troubleshooting.md**: WordPress REST API トラブルシューティング
- **docs/prompts/reve-writer-system-prompt.md**: Claude.ai（reve-writer）用システムプロンプト
