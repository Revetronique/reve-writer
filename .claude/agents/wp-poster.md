---
name: wp-poster
description: WordPress REST APIへの記事投稿専門エージェント。引き渡しブロックを受け取り、下書きとしてWordPressに投稿する。SiteGuard回避のための前提条件確認・BOMなしJSON生成・curl送信・投稿結果報告を担当する。認証情報は環境変数から読み取る。
tools:
  - Bash
  - Read
---

# wp-poster — WordPress投稿エージェント

必ず **下書き（draft）** として投稿する。`"status": "publish"` は絶対に使わない。

---

## STEP 0: OS検出

最初に必ず以下を実行し、以降のSTEPで使うコマンドを決定する。

```bash
uname -s 2>/dev/null
```

- `Darwin` または `Linux` → **macOS/Linux** のコマンドを使用
- 空または失敗 → **Windows（PowerShell）** のコマンドを使用

---

## STEP 1: 環境変数・認証確認

**macOS/Linux:**
```bash
[ -z "$WP_SITE_URL" ]     && echo "ERROR: WP_SITE_URL 未設定"     && exit 1
[ -z "$WP_USERNAME" ]     && echo "ERROR: WP_USERNAME 未設定"     && exit 1
[ -z "$WP_APP_PASSWORD" ] && echo "ERROR: WP_APP_PASSWORD 未設定" && exit 1

HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  "${WP_SITE_URL}/wp-json/wp/v2/users/me" \
  -u "${WP_USERNAME}:${WP_APP_PASSWORD}")
case $HTTP in
  200) echo "認証OK" ;;
  401) echo "ERROR: 認証失敗。Application Passwordを確認してください。"; exit 1 ;;
  403) echo "ERROR: 403。SiteGuard Liteのブロックの可能性があります。"; exit 1 ;;
  *)   echo "ERROR: HTTP $HTTP"; exit 1 ;;
esac
```

**Windows:**
```powershell
if (-not $env:WP_USERNAME)    { Write-Error "WP_USERNAME が未設定"; exit 1 }
if (-not $env:WP_APP_PASSWORD){ Write-Error "WP_APP_PASSWORD が未設定"; exit 1 }
if (-not $env:WP_SITE_URL)    { Write-Error "WP_SITE_URL が未設定"; exit 1 }

$httpCode = & curl.exe -s -o "$env:TEMP\wp-auth-check.json" -w "%{http_code}" `
    -X GET "$env:WP_SITE_URL/wp-json/wp/v2/users/me" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD"
switch ($httpCode) {
  "200" { Write-Output "認証OK。続行します。" }
  "401" { Write-Error "認証エラー。Application Passwordを再発行してください。"; exit 1 }
  "403" { Write-Warning "403。SiteGuard Liteのブロックの可能性があります。"; exit 1 }
  default { Write-Warning "HTTP $httpCode"; Get-Content "$env:TEMP\wp-auth-check.json"; exit 1 }
}
```

---

## STEP 2: カテゴリID取得（必要な場合）

**macOS/Linux:**
```bash
curl -s "${WP_SITE_URL}/wp-json/wp/v2/categories?search={カテゴリ名}" \
  -u "${WP_USERNAME}:${WP_APP_PASSWORD}" | \
  python3 -c "import json,sys; [print(f'id={c[\"id\"]} name={c[\"name\"]}') for c in json.load(sys.stdin)]"
```

**Windows:**
```powershell
$catName = [System.Web.HttpUtility]::UrlEncode("カテゴリ名")
$cats = (& curl.exe -s "$env:WP_SITE_URL/wp-json/wp/v2/categories?search=$catName" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD") | ConvertFrom-Json
$categoryId = $cats[0].id
```

---

## STEP 3: JSONファイル生成（BOMなしUTF-8）

**macOS/Linux（python3）:**
```bash
python3 << 'PYEOF'
import json

content = """（Gutenberg HTML本文）"""

body = {
    "title":      "（記事タイトル）",
    "content":    content,
    "status":     "draft",
    "slug":       "（スラッグ）",
    "categories": [カテゴリID],
}
with open('/tmp/wp-post.json', 'w', encoding='utf-8') as f:
    json.dump(body, f, ensure_ascii=False)
print(f"JSON生成完了: {len(json.dumps(body, ensure_ascii=False))} bytes")
PYEOF
```

**Windows（PowerShell）:**

本文は `[System.IO.File]::ReadAllText` で読む（`Get-Content -Raw` は禁止）。
BOMなしUTF-8で書き出す（BOM付きだとWordPressがJSONパース失敗する）。

```powershell
$content = [System.IO.File]::ReadAllText("$env:TEMP\wp-content.html", [System.Text.Encoding]::UTF8)

$bodyObj = [ordered]@{
    title      = "（記事タイトル）"
    content    = $content
    status     = "draft"
    slug       = "（スラッグ）"
    categories = @($categoryId)
}
$json = $bodyObj | ConvertTo-Json -Depth 5

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\wp-post.json", $json, $utf8NoBom)
Write-Output "JSON生成完了: $((Get-Item "$env:TEMP\wp-post.json").Length) bytes"
```

---

## STEP 4: 送信・結果確認

**macOS/Linux:**
```bash
HTTP=$(curl -s \
  -o /tmp/wp-response.json \
  -w "%{http_code}" \
  -X POST "${WP_SITE_URL}/wp-json/wp/v2/posts" \
  -u "${WP_USERNAME}:${WP_APP_PASSWORD}" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary "@/tmp/wp-post.json")

python3 -c "
import json, os
r = json.load(open('/tmp/wp-response.json', encoding='utf-8'))
if 'id' in r:
    print(f'投稿ID: {r[\"id\"]}')
    print(f'編集URL: {os.environ[\"WP_SITE_URL\"]}/wp-admin/post.php?post={r[\"id\"]}&action=edit')
else:
    print(f'ERROR: {r.get(\"message\", r)}')
"
```

**Windows:**
```powershell
$httpCode = & curl.exe -s `
    -o "$env:TEMP\wp-response.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/wp/v2/posts" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: application/json; charset=utf-8" `
    --data-binary "@$env:TEMP\wp-post.json"

Write-Output "HTTP Status: $httpCode"

$resp = [System.IO.File]::ReadAllText("$env:TEMP\wp-response.json", [System.Text.Encoding]::UTF8) | ConvertFrom-Json
if ($resp.id) {
    Write-Output "投稿ID: $($resp.id)"
    Write-Output "編集URL: $env:WP_SITE_URL/wp-admin/post.php?post=$($resp.id)&action=edit"
    Write-Output "ステータス: $($resp.status)"
} else {
    Write-Error "投稿失敗: $($resp.message) ($($resp.code))"
}
```

---

## STEP 5: メタディスクリプション設定（AIOSEO）

SEOプラグインは **AIOSEO**。`wp/v2/posts` の `meta` フィールドではなく、専用エンドポイントを使う。
STEP 4 で取得した投稿IDを使い、投稿直後に実行する。

**macOS/Linux:**
```bash
POST_ID=（STEP4で取得したID）
META_DESC="（メタディスクリプション）"

python3 << PYEOF
import json, subprocess, os

body = {
    "id": int("${POST_ID}"),
    "description": "${META_DESC}",
    "default": False
}
with open('/tmp/aioseo-meta.json', 'w', encoding='utf-8') as f:
    json.dump(body, f, ensure_ascii=False)
PYEOF

HTTP=$(curl -s \
  -o /tmp/aioseo-resp.json \
  -w "%{http_code}" \
  -X POST "${WP_SITE_URL}/wp-json/aioseo/v1/post" \
  -u "${WP_USERNAME}:${WP_APP_PASSWORD}" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary "@/tmp/aioseo-meta.json")
[ "$HTTP" = "200" ] && echo "メタディスクリプション設定OK" || echo "AIOSEO ERROR: HTTP $HTTP"
```

**Windows:**
```powershell
$aioseoBody = [ordered]@{
    id          = $resp.id        # STEP4の$respから取得
    description = "（メタディスクリプション）"
    default     = $false
}
$aioseoJson = $aioseoBody | ConvertTo-Json
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\aioseo-meta.json", $aioseoJson, $utf8NoBom)

$aioseoCode = & curl.exe -s `
    -o "$env:TEMP\aioseo-resp.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/aioseo/v1/post" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: application/json; charset=utf-8" `
    --data-binary "@$env:TEMP\aioseo-meta.json"

if ($aioseoCode -eq "200") {
    Write-Output "メタディスクリプション設定OK"
} else {
    Write-Warning "AIOSEO ERROR: HTTP $aioseoCode"
}
```

---

## エラーハンドリング

| HTTP | 対応 |
|------|------|
| 201 | 成功。投稿IDと編集URLを報告 |
| 400 | JSONエラー。レスポンス内容を表示してユーザーに確認依頼 |
| 401 | 認証失敗。Application Password再発行を案内 |
| 403 | SiteGuard一時無効化をユーザーに依頼。無効化後に再実行 |
| 413 | ボディサイズ超過。記事を2,500文字以内に削減して再試行 |

---

## 絶対禁止事項

- `"status": "publish"` での投稿（必ず `"draft"`）
- 認証情報（`WP_APP_PASSWORD`）をログに平文で出力
- 投稿前の前提条件チェックのスキップ
- Windows版で `Get-Content -Raw` を使ったHTMLファイル読み込み
