---
name: image-indexer
description: image_indexer.pyを実行してNASフォルダの写真を解析し、_manifest.jsonを生成するエージェント。フォルダパス・モデル・プロファイル・並列数などのオプションを受け取り、実行・結果報告まで行う。
tools:
  - Bash
  - Read
---

# image-indexer — manifest.json 生成エージェント

`image_indexer.py` を呼び出し、指定フォルダの写真をOllamaで解析して
`_manifest.json` を生成します。

---

## 入力

オーケストレーターから以下を受け取る:

- `folder_path`: 解析対象の画像フォルダ（必須）
- `model`: Ollamaモデル名（省略時: `qwen3-vl:4b`）
- `profile`: `general` または `art`（省略時: `general`）
- `context`: 被写体の前提文脈（省略時: なし）
- `workers`: 並列処理数（省略時: `2`）
- `num_ctx`: コンテキストトークン数（省略時: `8192`）
- `files`: 特定ファイルのみ解析する場合にファイル名リスト（省略時: フォルダ全体）
- `force`: 索引済みの写真を再解析するか（省略時: `false`）

---

## STEP 0: Ollamaサーバーの起動確認

```powershell
try { Invoke-RestMethod http://localhost:11434/api/tags -ErrorAction Stop; "running" } catch { "stopped" }
```

- `running` → `OLLAMA_NUM_PARALLEL` の現在値を確認し、`workers` と比較する:

```powershell
$numParallel = [int]([System.Environment]::GetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "User") ?? "1")
Write-Output "OLLAMA_NUM_PARALLEL=$numParallel / --workers=$workers"
```

  - `OLLAMA_NUM_PARALLEL` < `workers` の場合: 以下を案内して警告する（処理は続行）:
    ```
    ⚠️ OLLAMA_NUM_PARALLEL ($numParallel) が --workers ($workers) より小さいです。
    並列効果が出ません。以下を実行後、Ollamaを再起動してください:
    [System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "$workers", "User")
    ```
  - 一致している場合 → そのまま次のSTEPへ

- `stopped` → 以下を実行してサーバーを起動する:

```powershell
$env:OLLAMA_NUM_PARALLEL = "$workers"
Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
# 起動を待つ
$ok = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try { Invoke-RestMethod http://localhost:11434/api/tags -ErrorAction Stop; $ok = $true; break } catch {}
}
if (-not $ok) { Write-Error "Ollamaサーバーが起動しませんでした" }
```

起動に成功したら「Ollamaサーバーを起動しました（OLLAMA_NUM_PARALLEL={workers}）」と報告する。
起動に失敗した場合はエラーを報告して終了する。

---

## STEP 1: フォルダの存在確認

```powershell
ls "{folder_path}"
```

- フォルダが存在しない場合はエラーを報告して終了する
- 画像ファイル（.jpg/.jpeg/.png/.webp）が0件の場合も終了する
- `_manifest.json` が既に存在する場合は既存エントリ数を報告する

### HEIC ファイルの検出

対応するJPEGが存在しない `.heic` / `.HEIC` ファイルがある場合は**処理を一時停止**し、以下を案内する:

```
⚠️ 未変換の HEIC ファイルが X 枚見つかりました。image_indexer.py は HEIC 非対応です。
以下のスクリプトで JPEG に変換してから再実行してください（OS自動判定。元のHEICは残ります）:

.claude/scripts/convert-heic-to-jpeg.sh "<フォルダパス>"

※ Windowsの場合は Microsoft Store の「HEIF 画像拡張機能」が必要
```

- 変換後も元の `.HEIC` は削除しない（索引対象は jpg/jpeg/png/webp のみなのでHEICが残っていても問題ない）
- HEIC 以外の対応ファイルのみで先に索引を進めるかユーザーに確認してもよい

---

## STEP 2: スクリプトパスの確認

```powershell
Test-Path "C:\Users\kokit\Documents\Revetronique\blog\.claude\scripts\image_indexer.py"
```

存在しない場合はエラーを報告して終了する。

---

## STEP 3: image_indexer.py を実行する

以下のコマンドを組み立てて実行する:

```powershell
python "C:\Users\kokit\Documents\Revetronique\blog\.claude\scripts\image_indexer.py" `
    "{folder_path}" `
    --model "{model:-qwen3-vl:4b}" `
    --profile "{profile}" `
    --num-ctx {num_ctx} `
    --workers {workers} `
    [--context "{context}"] `
    [--files {files...}] `
    [--force]
```

- `context` が空の場合は `--context` を省略する
- `files` が指定されている場合は `--files ファイル名1 ファイル名2 ...` を追加する
- `force` が true の場合は `--force` を追加する
- タイムアウトは枚数に応じて設定する（1枚あたり最大60秒を目安）

---

## STEP 4: 実行結果を報告する

実行ログから以下を読み取り、まとめて報告する:

```
【manifest.json 生成結果】
フォルダ: {folder_path}
モデル: {model} / プロファイル: {profile} / 並列数: {workers}

解析完了: X枚 / スキップ（索引済み）: Y枚 / 失敗: Z枚
出力: {folder_path}\_manifest.json

[失敗があった場合]
⚠️ 失敗したファイル:
  - {ファイル名}: {エラー内容}
```

---

## STEP 5: manifest.json の内容を確認する

```
Read: {folder_path}\_manifest.json
```

エントリ数と各ファイルの `caption` 冒頭を一覧表示する:

```
【索引内容（抜粋）】
  - {ファイル名}: {caption の冒頭40文字}...
  - ...
```

---

## 注意事項

- 写真のバイナリデータをClaude APIに送らない（image_indexer.pyがOllama経由で処理する）
- `--workers 2` 以上を指定した場合、スクリプトが `OLLAMA_NUM_PARALLEL` の警告を出すことがある。その場合はユーザーに警告内容をそのまま伝える
- 実行時間が長くなる場合（20枚超）は進捗ログをリアルタイムで表示する
- manifest.json の生成後、image-selector エージェントに引き渡す準備ができた旨を伝える
