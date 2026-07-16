# smoke-test — システム疎通・動作確認

プロジェクト修正後やトラブル調査時に実施するスモークテスト。
全項目を上から順に実行し、チェックリスト形式で結果を報告する。

---

## 実行方法

```
/smoke-test               # 全項目
/smoke-test wp            # WP接続・投稿系のみ
/smoke-test notion        # Notion系のみ
/smoke-test agents        # サブエージェント系のみ
/smoke-test skills        # スキル系のみ
```

---

## グループA: WP接続・認証

### A-1. 認証確認

```powershell
$httpCode = & curl.exe -s -o "$env:TEMP\wp-auth.json" -w "%{http_code}" `
    "$env:WP_SITE_URL/wp-json/wp/v2/users/me" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD"
# 期待値: 200、name=revetronique
```

### A-2. テキストのみ下書き投稿

```powershell
$body = @{ title="【テスト】smoke-test"; content="<!-- wp:paragraph --><p>test</p><!-- /wp:paragraph -->"; status="draft"; slug="smoke-test-delete-me" }
$json = $body | ConvertTo-Json
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\smoke-post.json", $json, $utf8NoBom)
$httpCode = & curl.exe -s -o "$env:TEMP\smoke-post-resp.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/wp/v2/posts" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: application/json; charset=utf-8" `
    --data-binary "@$env:TEMP\smoke-post.json"
# 期待値: 201、status=draft
# → 取得した投稿IDを $testPostId に保存して以降のテストで使う
```

### A-3. 画像アップロード（Media API）

```powershell
# テスト用に任意のJPGファイルパスを指定する
$testImage = "Y:\Event\EXPO2025\PXL_20250814_050252933.jpg"
$httpCode = & curl.exe -s -o "$env:TEMP\smoke-media-resp.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/wp/v2/media" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: image/jpeg" `
    -H 'Content-Disposition: attachment; filename="smoke-test.jpg"' `
    --data-binary "@$testImage"
# 期待値: 201
# ❌ 403の場合: ConoHa WING WAF（OSコマンドインジェクション防御）が /wp-json/wp/v2/media を
#   ブロックしている。ConoHa管理パネル → WAF → 当該ルールにURL除外を追加すること。
#   WPプラグインのSiteGuard設定変更では解決しない。
```

### A-4. メタディスクリプション設定（AIOSEO）

```powershell
# SEOプラグインはAIOSEO。meta.the_page_meta_description は使用しない。
# フラット構造で POST /wp-json/aioseo/v1/post に送る。currentPostラッパー不要。
$aioseoBody = [ordered]@{ id=$testPostId; description="テスト用メタディスクリプション"; default=$false }
$aioseoJson = $aioseoBody | ConvertTo-Json
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\smoke-aioseo.json", $aioseoJson, $utf8NoBom)
$httpCode = & curl.exe -s -o "$env:TEMP\smoke-aioseo-resp.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/aioseo/v1/post" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: application/json; charset=utf-8" `
    --data-binary "@$env:TEMP\smoke-aioseo.json"
# 期待値: 200、{"success":true,"posts":{id}}
# 保存確認: GET /wp-json/aioseo/v1/post?postId={id} → description が設定値・default=false
```

### A-5. カテゴリ一覧取得

```powershell
$httpCode = & curl.exe -s -o "$env:TEMP\smoke-cats.json" -w "%{http_code}" `
    "$env:WP_SITE_URL/wp-json/wp/v2/categories?per_page=100" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD"
# 期待値: 200、カテゴリ一覧が返る
# 主要カテゴリID（変更時は更新すること）:
#   Travel=15, Event=7, 聖地巡礼=183
```

### A-6. テスト投稿の削除

```powershell
# A-2・A-3で作成したテスト投稿・メディアをWP管理画面から削除すること
# 投稿ID: $testPostId
```

---

## グループB: Notion連携

### B-1. 下書きフォルダ取得（notion-fetch）

```
notion-fetch で以下URLを取得:
https://app.notion.com/p/3746fa51aa01811cba49c0229d34654c
期待値: 下書きページ一覧が返る（タイトル「下書き」）
```

### B-2. 個別ページ取得・パース

```
下書きフォルダ内の任意のページURLを notion-fetch で取得。
期待値:
- ステータス行（「ステータス: 〇〇」）が読める
- --- 区切りより前がメタ情報、後が本文として取得できる
- NAS写真フォルダ・選定写真リストが確認できる
```

### B-3. ステータス更新

```
notion-update-page (command: update_content) で対象ページの
「ステータス: 〇〇」を別の値に変更後、notion-fetch で変更を確認してから元に戻す。
期待値: update → fetch → restore が全て成功
```

---

## グループC: サブエージェント

### C-1. proofreader

```
任意の下書き本文を proofreader エージェントに渡す。
期待する出力:
- 問題点リスト（★マーカー残存・スタイル違反・文字数）
- 総合判定（OK / 要修正）
```

### C-2. image-selector

```
manifest.json が存在するフォルダと下書き本文を image-selector エージェントに渡す。
期待する出力:
- 各H2セクションへの写真割り当て（または候補なし + [★写真:...]）
既知の動作: manifestと記事の内容が不一致の場合、全セクション「候補なし」と正しく判定する
```

### C-3. image-indexer（Ollama疎通確認）

```powershell
# Ollama稼働確認
& curl.exe -s "http://localhost:11434/api/tags"
# 期待値: モデル一覧JSON（qwen3-vl:4b 等が含まれる）
```

```
小規模フォルダ（数枚〜10枚程度）で image-indexer エージェントを起動。
期待する出力:
- 解析枚数・スキップ枚数・失敗枚数
- 各ファイルのcaption冒頭
注意: --workers のデフォルトは 2。OLLAMA_NUM_PARALLEL=2 に合わせること。
```

---

## グループD: スキル動作確認

### D-1. /precheck

```
/precheck {投稿ID}
期待する出力: 9項目のチェックリスト
注意: item5（メタディスクリプション）は AIOSEO API（/wp-json/aioseo/v1/post?postId=...）
      で取得した description 値・default フラグを確認する。
      meta.the_page_meta_description では取得できない。
```

### D-2. /edit-post

```
/edit-post 投稿ID {修正内容}
メタディスクリプション変更の場合: AIOSEO エンドポイントを使う（wp-poster.md STEP 5参照）
期待する出力: 「更新しました: {編集URL}」
```

### D-3. /index-photos

```
/index-photos {NASフォルダパス}
期待する動作:
1. 差分確認（未索引枚数／索引済み枚数を表示）
2. HEIC混在時は変換を案内してからJPGのみ処理
3. ユーザー確認後に image-indexer エージェント起動
4. 完了後に索引内容（ファイル名＋caption冒頭）を一覧表示
```

---

## 既知の問題・注意事項

| 問題 | 原因 | 対応 |
|------|------|------|
| 画像アップロードが403 | ConoHa WING WAF（OSコマンドインジェクション防御）の誤検知 | WAF設定で `/wp-json/wp/v2/media` を除外。WPプラグイン側では解決不可 |
| `meta.the_page_meta_description` が空 | AIOSEOは専用テーブルを使用。WP REST APIの `meta` フィールドには現れない | `POST /wp-json/aioseo/v1/post` に `{id, description, default:false}` のフラット構造で送る |
| AIOSEO POST で「Post ID is missing」 | `postId` / `post_id` キーは不可。`id` キーを使うこと | `{"id": 1234, "description": "...", "default": false}` |
| `currentPost` ラッパーで保存されない | AIOSEO はフラット構造を期待する | `currentPost` オブジェクトにネストしない |
| qwen3-vl に `think=False` で空応答 | qwen3-vl:4b 非対応パラメータ | image_indexer.py から `think=False` を削除済み（2026-07-16修正） |
| Ollama 並列効果なし | `OLLAMA_NUM_PARALLEL` < `--workers` | `[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "2", "User")` 後に再起動 |

---

## チェックリスト出力テンプレート

```
【smoke-test 結果】{実施日}

グループA: WP接続・投稿
  ✅/❌ A-1. 認証
  ✅/❌ A-2. テキスト投稿
  ✅/❌ A-3. 画像アップロード
  ✅/❌ A-4. メタディスクリプション（AIOSEO）
  ✅/❌ A-5. カテゴリ取得

グループB: Notion連携
  ✅/❌ B-1. 下書きフォルダ取得
  ✅/❌ B-2. 個別ページ取得
  ✅/❌ B-3. ステータス更新

グループC: サブエージェント
  ✅/❌ C-1. proofreader
  ✅/❌ C-2. image-selector
  ✅/❌ C-3. image-indexer（Ollama疎通）

グループD: スキル
  ✅/❌ D-1. /precheck
  ✅/❌ D-2. /edit-post
  ✅/❌ D-3. /index-photos

問題あり: {件数}件 → 詳細は上記
```
