---
name: index-photos
description: NAS写真フォルダをOllamaで解析して_manifest.jsonを生成する事前索引フロー。「○○の写真を索引して」「manifestを作って/更新して」等の依頼で使用する。差分のみ処理し、承認後にimage-indexerエージェントを起動する。
---

# index-photos — 写真の事前索引（_manifest.json 生成）

`_manifest.json` が存在しない、または未索引ファイルがあるフォルダを対象に、
`image-indexer` エージェント経由で `image_indexer.py` を実行して索引を生成・更新する。
**差分のみ処理する**（索引済みファイルはスキップ）。

写真のバイナリデータはClaude APIに送らない（解析はローカルOllamaで行う）。

## STEP 1: 差分の確認

フォルダ内の画像ファイル一覧を取得し、`_manifest.json` に未登録のファイルを差分抽出する。

```powershell
$folder = "Y:\Event\2026-06-makerfaire\"
$images = (ls $folder | Where-Object { $_.Extension -match '\.(jpg|jpeg|png|webp)$' }).Name
$manifest = if (Test-Path "$folder\_manifest.json") {
    (Get-Content "$folder\_manifest.json" -Raw | ConvertFrom-Json).PSObject.Properties.Name
} else { @() }
$unindexed = $images | Where-Object { $_ -notin $manifest }
Write-Output "未索引: $($unindexed.Count) 枚 / 索引済み: $($manifest.Count) 枚"
$unindexed
```

- `.heic`/`.HEIC` が混ざっている場合は `image_indexer.py` 非対応のため、先に
  `.claude/scripts/convert-heic-to-jpeg.sh` でJPEG化するよう案内する

## STEP 2: ユーザー確認

「未索引 X 枚 / 索引済み Y 枚」と未索引ファイル名を表示して確認を取る。OK後に次へ。

## STEP 3: image-indexer エージェント起動

未索引ファイルのみ `--files` で渡す。指示テンプレート:

```
以下を実行せよ:
- folder_path: {NAS写真フォルダのフルパス}
- model / profile / workers / context: {省略時はデフォルト値}
- files: {未索引ファイルのみ渡す場合はファイル名リスト}
- force: {再索引が必要な場合のみ true}
上記フォルダの写真をOllama経由で解析し、_manifest.json を生成（または更新）し、
索引結果（解析枚数・スキップ枚数・失敗枚数）を報告せよ。
バイナリデータをClaude APIに送らないこと。
```

- ユーザーが「`--force` で再索引して」と指定した場合はフォルダ全体を再解析する
- モデル・プロファイル等のオプションは `.claude/agents/image-indexer.md` を参照
- メディアアート等、見ただけでは正体が分からない被写体は `profile: art` と `context` の指定を提案する

## STEP 4: 結果表示

完了後、索引内容（ファイル名＋caption冒頭）を一覧表示する。

```
【索引内容（抜粋）】
  - {ファイル名}: {captionの冒頭40文字}...
```

索引完了後は、下書き投稿時（/post-draft）に `image-selector` が写真選定に利用できる。
