# WordPress REST API 投稿トラブルシューティング

## エラー早見表

| 症状 | 原因 | 対応 |
|------|------|------|
| 403 Powered by SiteGuard Lite（大きいボディ） | JSONが肥大化してSiteGuardのREST API制限に引っかかった可能性 | `Get-Content -Raw`を使っていないか確認。SiteGuardを一時無効化して切り分け |
| 403 Powered by SiteGuard Lite（全リクエスト） | SiteGuardのREST API制限が有効 | SiteGuardを一時無効化 |
| 403 Powered by SiteGuard Lite（画像POSTのみ。記事JSON POSTは通る） | **ConoHa WING側のサーバーレベルWAF**（「OSコマンドインジェクションからの防御」誤検知）。WPプラグインのSiteGuard Liteとは別物 | 下記「4. 画像アップロードのみ403になる」を参照 |
| 400 rest_invalid_json / Syntax error | JSONにBOMが混入 | BOMなしUTF-8で書き出す |
| 400 rest_invalid_json / Syntax error | `Get-Content -Raw`がオブジェクトを返す | `[System.IO.File]::ReadAllText`で読む |
| 401 Unauthorized | Application Passwordが不正 | WP管理画面でパスワードを再発行 |
| 200だが投稿されない | GETは通るがPOSTが弾かれている | 認証ヘッダーの確認、SiteGuard確認 |

---

## 原因別 詳細

### 1. SiteGuard Lite によるブロック

#### 症状
```
403 Forbidden
Powered by SiteGuard Lite
```

#### 原因A: REST APIアクセス制限が有効
SiteGuardの「REST APIアクセス制限」が有効になっているとすべてのREST APIリクエストをブロックする。

#### 原因B: JSONの肥大化によるブロック（最も遭遇しやすい）
小さいPOSTは通過するが、記事本文のような大きなボディがブロックされる場合は
JSONの肥大化が原因の可能性が高い。ConoHa WINGの`post_max_size`はデフォルト32MBなので
サーバー側の制限ではなく、`Get-Content -Raw`によるJSONオブジェクト化が原因のケースが多い。
→ **原因3（JSONが異常に肥大化する）を先に確認すること。**

#### 注意点
- SiteGuard Liteは **WordPressのフックレベル** で動作している
- `.htaccess` への例外追加は **効果なし**（`.htaccess`レベルでは動作していないため）
- SiteGuardのIPホワイトリスト機能は存在しない（または機能しない）
- `functions.php` への `rest_pre_dispatch` フィルター追加も **効果なし**（SiteGuardがより早いフックで遮断するため）

#### 対応
WP管理画面 → プラグイン → SiteGuard Lite を **一時的に無効化** して投稿後に再有効化する。

---

### 2. JSONにBOMが混入する（400 Syntax error）

#### 症状
```json
{"code":"rest_invalid_json","message":"無効な JSON ボディが渡されました。","data":{"status":400,"json_error_code":4,"json_error_message":"Syntax error"}}
```

#### 原因
PowerShellの `[System.Text.Encoding]::UTF8` はBOM付きUTF-8を使用する。  
ファイル先頭の `EF BB BF`（BOM）がJSONのパースを壊す。

#### 対応
```powershell
# NG: BOM付き
[System.IO.File]::WriteAllText($path, $json, [System.Text.Encoding]::UTF8)

# OK: BOMなし
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($path, $json, $utf8NoBom)
```

---

### 3. JSONが異常に肥大化する（3MB超）

#### 症状
JSONファイルが数MB以上になり、SiteGuardに弾かれる。

#### 原因A: `Get-Content -Raw` がオブジェクトを返す
```powershell
# NG: PSPath等のメタデータを含むオブジェクトがシリアライズされる
$content = Get-Content -Path "file.html" -Raw -Encoding UTF8
$body = @{ content = $content } | ConvertTo-Json  # contentがオブジェクトになる
```

ConvertTo-Json でシリアライズすると `content` フィールドが `{"value":"...","PSPath":"...","PSParentPath":"..."}` のような形になり、ファイル内容の数百倍に膨張する。

#### 対応A
```powershell
# OK: 純粋な文字列として読み込む
$content = [System.IO.File]::ReadAllText("file.html", [System.Text.Encoding]::UTF8)
```

#### 原因B: PowerShell 5.1 の ConvertTo-Json が \uXXXX エスケープする
日本語文字が `どうも`（どうも）のようにエスケープされ、ファイルサイズが2〜3倍になる。ただし **JSONとしては有効** なので、そのまま送信して問題ない。エスケープを戻す regex 処理を加えると逆にJSONが壊れるため、対処不要。

---

### 4. 画像アップロードのみ403になる（ConoHa WING側WAF）

#### 症状
記事投稿（`POST /wp/v2/posts` のJSON）や `GET /wp/v2/media` は通るのに、
画像のバイナリPOST（`POST /wp/v2/media`）だけが403 Forbidden（Powered by SiteGuard Lite）になる。
WPプラグインのSiteGuard Lite設定（CAPTCHA・WAFチューニング・REST API制限）をすべて無効化しても変化しない。
DELETEメソッドも同じ理由で403になることがある。

#### 原因
WordPressプラグインのSiteGuard Liteではなく、**ConoHa WING管理パネル側のサーバーレベルWAF**が原因。
「OSコマンドインジェクションからの防御」ルール（パターン `<??>` 等）が、JPEGバイナリ内に偶然含まれる
`<?` に似たバイト列（EXIF等のメタデータ含む）を誤検知（false positive）してブロックしている。
このWAFはWordPressのフックより手前（nginx層）で動作するため、プラグイン側の設定は効かない。

#### 切り分け方
1. `GET /wp-json/wp/v2/media?per_page=1` → 200か確認（認証・REST APIの生死を確認）
2. `POST /wp-json/wp/v2/posts`（小さいJSONボディ）→ 201か確認（POST自体がブロックされていないか確認）
3. 1, 2が通って画像バイナリPOSTのみ403なら、ファイルアップロード検知のWAFルールが濃厚

#### 対応
- **対応A（恒久対応）**: ConoHa WING管理パネルのWAF設定で、該当ルール（OSコマンドインジェクション防御）に
  対象URL（`/wp-json/wp/v2/media`）の除外設定を追加してもらう。一度設定すれば以降は通る
- **対応B（一時回避）**: アップロード元で画像を再エンコードしてからPOSTする。バイト列が変わるため
  誤検知を回避できることが確認されている。
  - macOS: `sips -s format jpeg input.jpg -o output.jpg`
  - Windows: `sips`相当のコマンドは無いが、PowerShell標準の`System.Drawing`（.NET Framework、追加インストール不要）で同様に再保存できる
    ```powershell
    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile("input.jpg")
    $img.Save("output.jpg", [System.Drawing.Imaging.ImageFormat]::Jpeg)
    $img.Dispose()
    ```

---

## 正しい投稿コード（Windows PowerShell 5.1）

```powershell
# 1. コンテンツをBOMなし文字列で読み込む
$content = [System.IO.File]::ReadAllText("path\to\content.html", [System.Text.Encoding]::UTF8)

# 2. ボディを構築
$bodyObj = [ordered]@{
    title   = "記事タイトル"
    content = $content
    status  = "draft"
    slug    = "article-slug"
    meta    = @{ the_page_meta_description = "メタディスクリプション" }
}
$json = $bodyObj | ConvertTo-Json -Depth 5

# 3. BOMなしUTF-8でJSONファイルを書き出す
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText("$env:TEMP\wp-post.json", $json, $utf8NoBom)

# 4. curl.exe で送信（Invoke-RestMethod より安定）
$result = & curl.exe -s -o "$env:TEMP\wp-response.json" -w "%{http_code}" `
    -X POST "$env:WP_SITE_URL/wp-json/wp/v2/posts" `
    -u "$env:WP_USERNAME`:$env:WP_APP_PASSWORD" `
    -H "Content-Type: application/json; charset=utf-8" `
    --data-binary "@$env:TEMP\wp-post.json"

if ($result -eq "201") {
    $resp = Get-Content "$env:TEMP\wp-response.json" -Raw | ConvertFrom-Json
    Write-Output "投稿ID: $($resp.id)"
    Write-Output "編集画面: $env:WP_SITE_URL/wp-admin/post.php?post=$($resp.id)&action=edit"
} else {
    Write-Output "エラー HTTP $result"
    Get-Content "$env:TEMP\wp-response.json" -Raw
}
```

---

## 認証の確認方法

投稿前に認証が通っているか確認する：

```powershell
$creds = "USERNAME:APP_PASSWORD"
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($creds))
Invoke-RestMethod -Uri "$env:WP_SITE_URL/wp-json/wp/v2/users/me" `
    -Headers @{ "Authorization" = "Basic $encoded" } | Select-Object id, name
```

`id` と `name` が返れば認証OK。

---

## 文字数制限ガイドライン

SiteGuard LiteのPOSTボディサイズ制限に対応するため、記事本文は **2,500文字以内** を目安とする。

| 目安 | 状態 |
|------|------|
| ~2,500文字 | SiteGuard制限内（問題なし） |
| 2,500〜5,000文字 | 要注意（環境によってブロックされる可能性） |
| 5,000文字超 | 高確率でブロック。SiteGuard一時無効化が必要 |

**文字数を節約するポイント:**
- 概要テーブルは冒頭に1つのみ（末尾の再掲は省く）
- 各セクションは「概要→詳細→感想」の3段構成で簡潔に
- アフィリエイトブロックのHTMLは最小限にする
