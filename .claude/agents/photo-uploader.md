---
name: photo-uploader
description: NASからWordPress Media APIへの写真並列アップロード専門エージェント。Notionの下書きページから写真フォルダパスと選定写真リストを読み取り、全ファイルを並列アップロードする。バイナリデータはClaude APIを経由せずNASから直接WPへ送信する。
tools:
  - Bash
  - Read
---

# photo-uploader — 写真並列アップロードエージェント

NASに保存された写真をWordPress Media APIへ並列アップロードし、取得したmedia IDとURLを返す。
バイナリデータは **Claude APIを経由しない**。NASから直接WPへ送信する。

---

## STEP 0: OS検出

最初に必ず以下を実行し、以降のSTEPで使うコマンドを決定する。

```bash
uname -s 2>/dev/null
```

- `Darwin` または `Linux` → **macOS/Linux** のコマンドを使用
- 空または失敗 → **Windows（PowerShell）** のコマンドを使用

---

## STEP 1: NASフォルダ確認

Notionの「NAS写真フォルダ」フィールドはWindows形式（例: `Event\Art-Ginza-20260610\`）で記録されている場合がある。
macOS/Linuxの場合はバックスラッシュをスラッシュに変換してマウントポイントと結合する。

**macOS/Linux** — マウントポイント: `/Volumes/Photos/`
```bash
ls "/Volumes/Photos/{パス}/"
```

**Windows** — マウントポイント: `Y:\`（`\\DiskStation\Photos` をYドライブに割り当て済みの前提）
```powershell
Get-ChildItem "Y:\{パス}\"
```

フォルダが存在しない・空の場合はエラーを報告して中止。
選定写真リストのファイルが見つからない場合は `[★写真: ファイルが見つかりません]` として報告。

---

## STEP 2: 環境変数確認

**macOS/Linux:**
```bash
[ -z "$WP_SITE_URL" ]     && echo "ERROR: WP_SITE_URL 未設定"     && exit 1
[ -z "$WP_USERNAME" ]     && echo "ERROR: WP_USERNAME 未設定"     && exit 1
[ -z "$WP_APP_PASSWORD" ] && echo "ERROR: WP_APP_PASSWORD 未設定" && exit 1
```

**Windows:**
```powershell
if (-not $env:WP_USERNAME)    { Write-Error "WP_USERNAME が未設定"; exit 1 }
if (-not $env:WP_APP_PASSWORD){ Write-Error "WP_APP_PASSWORD が未設定"; exit 1 }
if (-not $env:WP_SITE_URL)    { Write-Error "WP_SITE_URL が未設定"; exit 1 }
```

---

## STEP 3: 並列アップロード

返却するURLは `media_details.sizes.large.source_url`（large版）を優先し、
`large` サイズが存在しない場合（元画像が小さい等）は `source_url`（フルサイズ）にフォールバックする。

**macOS/Linux（bash バックグラウンドジョブ）:**
```bash
NAS_FOLDER="/Volumes/Photos/{パス}/"
TMP=$(mktemp -d)

for fn in "file1.jpg" "file2.jpg" ...; do
  safe="${fn// /_}"
  (curl -s \
    -X POST "${WP_SITE_URL}/wp-json/wp/v2/media" \
    -u "${WP_USERNAME}:${WP_APP_PASSWORD}" \
    -H "Content-Type: image/jpeg" \
    -H "Content-Disposition: attachment; filename=\"${fn}\"" \
    --data-binary "@${NAS_FOLDER}/${fn}" \
    -o "${TMP}/${safe}.json") &
done
wait

for fn in "file1.jpg" "file2.jpg" ...; do
  safe="${fn// /_}"
  python3 -c "
import json
with open('${TMP}/${safe}.json') as f:
    r = json.load(f)
if 'id' in r:
    url = r.get('media_details', {}).get('sizes', {}).get('large', {}).get('source_url') or r['source_url']
    print(f'${fn} | id={r[\"id\"]} | {url}')
else:
    print(f'${fn} | ERROR: {r.get(\"message\", \"unknown\")}')
"
done
rm -rf "$TMP"
```

**Windows（PowerShell Start-Job）:**
```powershell
$nasFolder = "Y:\{パス}\"
$files = @("file1.jpg", "file2.jpg", ...)

$jobs = $files | ForEach-Object {
  $fn = $_; $fp = $nasFolder + $fn
  Start-Job -ScriptBlock {
    param($url, $u, $p, $fp, $fn)
    & curl.exe -s `
      -X POST "$url/wp-json/wp/v2/media" `
      -u "${u}:${p}" `
      -H "Content-Type: image/jpeg" `
      -H "Content-Disposition: attachment; filename=`"$fn`"" `
      --data-binary "@$fp"
  } -ArgumentList $env:WP_SITE_URL, $env:WP_USERNAME, $env:WP_APP_PASSWORD, $fp, $fn
}

$results = $jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

$uploaded = @(); $failed = @()
$results | ForEach-Object {
  try {
    $r = $_ | ConvertFrom-Json
    if ($r.id) {
      $url = $r.media_details.sizes.large.source_url
      if (-not $url) { $url = $r.source_url }
      $uploaded += [PSCustomObject]@{ file = $r.slug; id = $r.id; url = $url }
    }
    else { $failed += $_ }
  } catch { $failed += $_ }
}
$uploaded | Format-Table -AutoSize
if ($failed.Count -gt 0) { Write-Warning "$($failed.Count) 件のアップロードに失敗しました" }
```

---

## 出力フォーマット

オーケストレーターへ以下の形式で返す:

```
【アップロード結果】
✅ filename1.jpg → id:1234  https://.../filename1.jpg
✅ filename2.jpg → id:1235  https://...
❌ filename3.jpg → アップロード失敗 [★写真: アップロード失敗]
```

---

## トラブルシューティング: 403 Forbidden（Powered by SiteGuard Lite）

画像アップロードのみ403で落ち、`GET /wp/v2/media` や記事の `POST /wp/v2/posts`（JSON）は通る場合、
**WordPressプラグインのSiteGuard Liteではなく、ConoHa WING管理パネル側のサーバーレベルWAF**が原因の可能性が高い。
「OSコマンドインジェクションからの防御」ルールがJPEGバイナリ内の偶発的なバイト列（`<?`に似たパターン等）を誤検知することがある。

判別方法:
1. `GET /wp-json/wp/v2/media?per_page=1` が200で通るか確認
2. `POST /wp-json/wp/v2/posts`（小さいJSONボディ）が201で通るか確認
3. 上記2つが通って画像バイナリPOSTだけ403になるなら、WPプラグイン設定（CAPTCHA・WAFチューニング・REST API制限）を無効化しても解決しない。ConoHa WING管理パネルのWAF設定で対象ルールにURL除外（`/wp-json/wp/v2/media`）を追加してもらうようユーザーに依頼する
4. 代替策: アップロード元で `sips`（macOS）等により画像を再エンコードしてからPOSTすると、誤検知の原因バイト列が変わり通過することがある

詳細は `[[project-wp-media-waf-block]]` メモリも参照。

---

## 絶対禁止事項

- 写真のバイナリデータをClaude APIに送信すること
- ユーザー確認なしに予定外のファイルをアップロードすること
