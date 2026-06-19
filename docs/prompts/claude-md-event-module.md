# イベント・お出かけ記事 仕様リファレンス

> **このモジュールは CLAUDE.md に統合済みです（2026-06）。**
> 以下の内容は参照用として残しています。実際の動作は CLAUDE.md が優先されます。

---

## イベント・お出かけ記事

### 記事タイプ定義

| タイプ | 用途 | Notion DB | 典型的な記事 |
|---|---|---|---|
| Type D | イベントレポート | Events DB (カテゴリ=イベント) | 展示会、カンファレンス、ライブ、即売会 |
| Type E | お出かけレポート | Events DB (カテゴリ=お出かけ) | 日帰り旅行、食レポ、観光 |

### Notion連携: Events DB

#### 記事生成フロー

1. Events DB から ステータス = "素材整理完了" のレコードを取得
2. イベント名、日付、場所、カテゴリ、メモ、見出し構成、写真選定リスト を読み込む
3. Writing Style ページからスタイルルールを取得
4. 記事タイプ（Type D or E）に応じたGutenbergテンプレートを選択
5. メモの内容をテンプレートの各セクションに配置・文章化
6. NAS の写真フォルダからファイル名一覧を取得（ls のみ）
7. 写真選定リストとファイル名をマッチング
8. マッチ結果をユーザーに確認表示
9. 承認後、curl で WordPress にメディアアップロード
10. 画像の media ID と URL をブロックHTMLに埋め込み
11. WP REST API で **下書き (status: draft)** 投稿
12. Notionの下書きページのステータスを "投稿済み" に更新
13. 「下書き投稿しました: [編集URL]」と表示

#### 制約（聖地巡礼と共通）

- WordPress投稿は**必ず draft**。公開は手動。
- 写真のバイナリデータを Claude API に送信しない。
- NASアクセスは SMB マウント（LAN内のみ）。
- アップロード前にユーザー確認を必ず挟む。

---

### 文章生成ルール

#### 共通スタイル（全記事タイプ共通）

- 冒頭: 「どうも、Reveです。」
- 締め: 「もし参考になれば幸いです。」
- 見出し: 【】形式（例: 【会場の様子】）
- 一人称: 「当方」または省略
- 語尾: です・ます調、会話的で丁寧だが堅すぎない
- 適度にカジュアル表現を混ぜる:（汗）、ｗ、「〜なんですよね」等
- 段落は3〜4文で改行（読みやすさ重視）

#### イベント記事（Type D）固有ルール

- イベントの正式名称を必ず1回はフルで記載
- 各見どころセクションは「概要 → 詳細 → 感想」の3段構成
- 講演内容は要約のみ（引用する場合は発言者名と文脈を明記）
- 技術イベントではスペック・型番を正確に記載（メモの数字をそのまま使う）
- 「次回も行きたい」「来年は○○に注目」など前向きな締めを心がける

#### お出かけ記事（Type E）固有ルール

- アクセス情報を冒頭寄りに配置（読者がすぐ使える位置）
- 食事セクションは価格を必ず記載
- 季節・天候の影響がある場合は言及する
- 「○○がおすすめです」より「当方は○○が気に入りました」（押し付けない）

#### 文章化の変換ルール

メモの箇条書きを文章化する際のルール:

```
【メモ（入力）】
- Cherry MX互換、基板4層、KiCad設計
- 価格 ¥12,000（BOOTH販売あり）
- 感想: キーキャップの触り心地が独特

【文章化（出力）】
こちらはCherry MX互換のスイッチを採用した自作キーボードで、
基板は4層構成、KiCadで設計されているとのこと。
価格は12,000円で、BOOTHでも販売されています。
実際に触らせていただいたのですが、キーキャップの触り心地が
独特で、これは好みが分かれそうなところですね。
```

変換時の注意:
- メモの箇条書きをそのまま並べただけの文章にしない
- 「〜とのこと」「〜だそうです」で伝聞と体験を区別する
- 感想メモは「実際に〜してみたのですが」等の体験描写に展開する
- 数字・固有名詞はメモの記載をそのまま保持（勝手に変えない）
- メモに感想がないセクションでも、最低1文は所感を入れる
  → **[★要加筆: ここに感想を追記]** とプレースホルダーを置く

---

### Gutenbergブロックテンプレート

#### Type D: イベントレポート

```html
<!-- wp:paragraph -->
<p>どうも、Reveです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{event_date}} に {{event_name}} に行ってきました。{{intro_text}}</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【イベント概要】</h2>
<!-- /wp:heading -->

<!-- wp:table {"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody>
<tr><th>イベント名</th><td>{{event_name}}</td></tr>
<tr><th>開催日</th><td>{{event_date}}</td></tr>
<tr><th>会場</th><td>{{venue}}</td></tr>
<tr><th>公式サイト</th><td><a href="{{official_url}}">{{official_url}}</a></td></tr>
</tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>{{venue_atmosphere}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{photo_venue_url}}" alt="{{event_name}} 会場の様子"/>
<figcaption>{{venue_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== 見どころセクション（メモのセクション数に応じて繰り返し） ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【{{highlight_title}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{highlight_overview}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{highlight_detail}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{highlight_photo_url}}" alt="{{highlight_title}}"/>
<figcaption>{{highlight_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>{{highlight_impression}}</p>
<!-- /wp:paragraph -->

<!-- ===== /見どころセクション ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【会場グルメ・購入品】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{food_and_goods}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{food_photo_url}}" alt="{{food_caption}}"/>
<figcaption>{{food_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== アフィリエイトリンク挿入ポイント ===== -->
<!-- wp:paragraph -->
<p>{{affiliate_block}}</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【まとめ】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{summary}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もし参考になれば幸いです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【イベント情報】</h2>
<!-- /wp:heading -->

<!-- wp:table {"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody>
<tr><th>イベント名</th><td>{{event_name}}</td></tr>
<tr><th>開催日</th><td>{{event_date}}</td></tr>
<tr><th>会場</th><td>{{venue}}</td></tr>
<tr><th>アクセス</th><td>{{access_info}}</td></tr>
<tr><th>入場料</th><td>{{admission}}</td></tr>
<tr><th>公式サイト</th><td><a href="{{official_url}}" target="_blank" rel="noopener noreferrer">{{official_url_display}}</a></td></tr>
</tbody></table></figure>
<!-- /wp:table -->
```

#### Type E: お出かけレポート

```html
<!-- wp:paragraph -->
<p>どうも、Reveです。</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>{{destination}} に行ってきたので、レポートします。{{intro_text}}</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【アクセス】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{access_detail}}</p>
<!-- /wp:paragraph -->

<!-- ===== アフィリエイト挿入ポイント: 交通系 ===== -->

<!-- ===== スポットセクション（訪問順に繰り返し） ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【{{spot_name}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{spot_description}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{spot_photo_url}}" alt="{{spot_name}}"/>
<figcaption>{{spot_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>{{spot_impression}}</p>
<!-- /wp:paragraph -->

<!-- ===== /スポットセクション ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【ランチ: {{restaurant_name}}】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{food_description}}</p>
<!-- /wp:paragraph -->

<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large">
<img src="{{food_photo_url}}" alt="{{restaurant_name}} {{menu_item}}"/>
<figcaption>{{food_caption}}</figcaption>
</figure>
<!-- /wp:image -->

<!-- ===== アフィリエイト挿入ポイント: グルメ系 ===== -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【まとめ】</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>{{summary}}</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>もし参考になれば幸いです。</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">【基本情報】</h2>
<!-- /wp:heading -->

<!-- wp:table {"className":"is-style-simple"} -->
<figure class="wp-block-table is-style-simple"><table><tbody>
<tr><th>場所</th><td>{{destination}}</td></tr>
<tr><th>住所</th><td>{{address}}</td></tr>
<tr><th>営業時間</th><td>{{hours}}</td></tr>
<tr><th>定休日</th><td>{{closed_days}}</td></tr>
<tr><th>料金</th><td>{{price}}</td></tr>
<tr><th>公式サイト</th><td><a href="{{official_url}}" target="_blank" rel="noopener noreferrer">{{official_url_display}}</a></td></tr>
<tr><th>Google Maps</th><td><a href="https://www.google.com/maps?q={{lat}},{{lng}}" target="_blank" rel="noopener noreferrer">地図を開く</a></td></tr>
</tbody></table></figure>
<!-- /wp:table -->
```

---

### プレースホルダーと加筆マーカー

テンプレートの `{{...}}` はNotionデータで自動置換する。
データが不足している場合は以下のマーカーを挿入し、人間の加筆を促す:

| マーカー | 意味 |
|---|---|
| `[★要加筆: 感想]` | メモに感想がなく、体験ベースの記述が必要 |
| `[★要加筆: 詳細]` | メモの情報が不足、現地の記憶で補完が必要 |
| `[★要確認: {{内容}}]` | 数字や固有名詞がメモから読み取れず確認が必要 |
| `[★写真: {{説明}}]` | 該当する写真がNAS内で見つからなかった |
| `[★アフィリエイト: {{種別}}]` | アフィリエイトリンクの挿入候補（人間が選定） |

WordPress下書きをエディタで開いた際、★マーカーを検索すれば加筆箇所が一覧できる。

---

### WordPress投稿パラメータ

```json
{
  "title": "【イベントレポート】{{event_name}}に行ってきた（{{year}}年）",
  "content": "{{generated_gutenberg_html}}",
  "status": "draft",
  "slug": "{{english_slug}}",
  "categories": ["{{category_id}}"],
  "tags": ["{{tag1}}", "{{tag2}}"],
  "meta": {
    "the_page_meta_description": "{{meta_description}}"
  }
}
```

タイトルパターン:
- Type D: `【イベントレポート】{{event_name}}に行ってきた（{{year}}年）`
- Type E: `【お出かけ】{{destination}} {{activity}}レポート（{{year}}年）`

スラッグ:
- Type D: `event-{{english_event_name}}-{{year}}` （例: `event-makerfaire-tokyo-2026`）
- Type E: `visit-{{english_destination}}-{{year}}` （例: `visit-kozushima-2026`）

メタディスクリプション:
- 120文字以内で「イベント名 + 何が見られるか + 一言感想」を含める
- 例: 「Maker Faire Tokyo 2026に行ってきました。個人開発の自作キーボードや基板が面白かった！会場の様子と見どころをレポートします。」

---

### NAS写真フォルダ命名規則

Events DB 用の写真フォルダ:

```
photos/events/{{YYYY-MM}}-{{english_event_name}}/
```

例:
- `photos/events/2026-06-makerfaire/`
- `photos/events/2026-07-kozushima/`

フォルダ内構成（推奨）:
```
2026-06-makerfaire/
├── all/           ← 撮影した全写真（iPad/スマホから取り込み）
└── selected/      ← 記事用に選定した写真（ここからアップロード）
```

写真選定リスト（Events DB の「写真選定リスト」フィールド）に
`selected/` 内のファイル名を記録。Claude Code はこのリストのみ参照。

---

### Claude Code 呼び出しパターン

#### 基本（1コマンドで下書き生成）

```
> Events DBの「Maker Faire Tokyo 2026」から Type D で下書きを作って。
```

#### 写真なし（テキストのみ先に生成）

```
> Events DBの「Maker Faire Tokyo 2026」からテキストだけ下書きして。
> 写真は後で手動で入れる。
```

#### メモ追加後の再生成

```
> Events DBの「Maker Faire Tokyo 2026」のメモを更新したので、
> 見どころ②のセクションだけ再生成して。
```

#### 複数イベントの一括下書き

```
> Events DB でステータスが「素材整理完了」のイベントを全部
> 下書き生成して。写真は後で入れるのでテキストのみで。
```

---

### 公開前チェック（Claude Code で実行可能な項目）

Claude Code に「公開前チェックして」と指示した場合、以下を自動確認:

1. タイトルにイベント名と年が含まれるか
2. スラッグが英語で設定されているか
3. アイキャッチ画像が設定されているか
4. カテゴリ・タグが設定されているか
5. メタディスクリプションが記入されているか（120文字以内）
6. 全画像に alt 属性があるか
7. ★マーカーが残っていないか（残っていれば一覧表示）
8. 内部リンク候補の提案（過去記事から関連しそうなもの）
9. 文字数カウント（2,000〜2,500文字の目安内か）

結果をチェックリスト形式で表示し、問題があれば修正を提案。
