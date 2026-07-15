---
name: rename-photos
description: NASに追加した写真をファイル命名規則（YYYYMMDD-{slug}-{NNNN}.jpg）で一括リネームするフロー。「○○の写真をリネームして」等の依頼で使用する。スラッグ候補の提示・確認後にrename-photos.shを実行し、聖地巡礼の場合はVisits DBに書き戻す。
---

# rename-photos — NAS写真の一括リネーム

新規写真をNASに追加した後、`CLAUDE.local.md` の命名規則に従ってリネームする。

**形式:** `YYYYMMDD-{slug}-{NNNN}.jpg`

| 要素 | 内容 |
|---|---|
| 日付 | EXIFのDateTimeOriginalから取得（EXIFなしの場合はファイル更新日時） |
| slug | 場所名・イベント名（実行時に手動指定） |
| 連番 | 4桁。フォルダ内の既存ファイルと重複しないよう採番 |

## STEP 0: HEIC変換（必要な場合）

`.heic`/`.HEIC` が含まれる場合は先にJPEGへ変換する（元HEICは残す）:

```bash
.claude/scripts/convert-heic-to-jpeg.sh "<ファイルまたはフォルダのパス>"
```

- Windowsの場合はMicrosoft Storeの「HEIF 画像拡張機能」が必要

## STEP 1: ファイル一覧の取得

対象フォルダのファイル名一覧を `ls` で取得し、リネーム対象（未リネームのファイル）を把握する。
既に `YYYYMMDD-{slug}-{NNNN}` 形式のファイルはスクリプト側でスキップされ、連番はその続きから採番される。

## STEP 2: スラッグ候補の提示

- **聖地巡礼写真:** 聖地スポットDBからスラッグ一覧を取得して候補を提示する
- **イベント・お出かけ写真:** フォルダ名やイベント名から英小文字ハイフン区切りのslugを提案する
- ファイル単位で別slugを指定したい場合（例: `20240503-numazu-mito-house-0001.jpg`）はユーザーの指示に従う

## STEP 3: ユーザー確認とリネーム実行

日付・slug・対象ファイル数を表示して確認を取り、OK後に実行する:

```bash
.claude/scripts/rename-photos.sh <フォルダパス> <YYYYMMDD> <slug>
# 例: .claude/scripts/rename-photos.sh /y/Event/2026-06-makerfaire/ 20260601 makerfaire-tokyo-2026
```

- Git Bashからは `Y:\` を `/y/` として指定する
- 対象拡張子: jpg / jpeg / png / webp（大文字小文字区別なし）

## STEP 4: Notionへの書き戻し（聖地巡礼のみ）

リネーム後のファイル名を Visits DB の `選定写真リスト` フィールドに書き戻す。

## STEP 5: 索引の案内

リネーム後、`_manifest.json` の索引が必要なら `/index-photos` を案内する
（リネームで旧ファイル名の索引エントリは無効になるため、再索引を推奨）。
