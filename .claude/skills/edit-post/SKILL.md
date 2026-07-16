---
name: edit-post
description: 既存WordPress投稿の部分修正フロー。「投稿ID nnnn の○○セクションを書き直して」「メタディスクリプションを変えて」「タイトル/スラッグを変えて」等の依頼で使用する。全文取得→該当ブロック差し替え→全文更新→編集URL表示を行う。
---

# edit-post — 既存投稿の修正

投稿IDはWordPress管理画面のURL（`post.php?post=1234`）で確認する。
IDが不明な場合は `GET /wp-json/wp/v2/posts?search={キーワード}` で候補を提示して確認する。

## パターン1: 特定セクションの書き直し

1. `GET /wp-json/wp/v2/posts/{id}?context=edit` で全文取得（`content.raw` を使う）
2. 該当Gutenbergブロックをブロックコメント（`<!-- wp:heading -->` 等）で特定
3. 指示に従って該当ブロックの内容を差し替え（他ブロックには手を触れない）
4. `POST /wp-json/wp/v2/posts/{id}` で全文更新
5. 「更新しました: [編集URL]」と表示

書き直し時もCLAUDE.mdの文章スタイル（Reve文体・★マーカー運用・数字/固有名詞の保持）に従う。

## パターン2: メタディスクリプションのみ変更

```json
{ "meta": { "the_page_meta_description": "（120文字以内）" } }
```

本文（content）を送らず、変更するフィールドだけをPOSTする。

## パターン3: タイトル・スラッグのみ変更

```json
{ "title": "（新タイトル）", "slug": "（新スラッグ）" }
```

- スラッグ変更時はRedirectionプラグインが旧URL→新URLの301を自動作成する（設定済み前提）
- スラッグはCLAUDE.mdの「スラッグ命名規則」に従う

## 技術仕様（共通）

送信方法は `.claude/agents/wp-poster.md` の技術仕様が正。要点:

- 本文ファイルの読み込みは `[System.IO.File]::ReadAllText`（`Get-Content -Raw` は禁止。JSONが数百倍に肥大化する）
- JSONは**BOMなしUTF-8**で書き出す（`[System.Text.UTF8Encoding]::new($false)`）
- 送信は `Invoke-RestMethod` ではなく `curl.exe --data-binary` を使う
- 全文POSTはConoHa WINGのデフォルト制限（32MB）に対して数十KB以下なので問題なし。
  ただし本文2,500字超はSiteGuardのPOST制限に注意（403時は `docs/design/wp-post-troubleshooting.md` 参照）
- ステータスは変更しない（draftはdraftのまま。`"status": "publish"` は絶対に送らない）

## 更新後

必ず編集URL（`{WP_SITE_URL}/wp-admin/post.php?post={id}&action=edit`）を表示し、目視確認を促す。
