#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_indexer.py  —  reve-writer 写真索引ジェネレータ

NASフォルダ内の画像をローカル Qwen3-VL (Ollama) で解析し、
フォルダ直下に `_manifest.json` を生成する。

reve-writer (Claude.ai) はこの manifest を読み、下書きの
`[★写真: {{説明}}]` プレースホルダに最適な写真を割り当てる。
本スクリプトの役割は「画像の中身をテキスト化する」ところまで。

前提:
    pip install ollama pillow
    ollama pull qwen3-vl:8b        # VRAM 8GBなら qwen3-vl:4b
    ollama serve  (通常は自動起動)

使い方:
    python image_indexer.py "Y:\\photos\\events\\2026-06-makerfaire"
    python image_indexer.py <folder> --model qwen3-vl:8b --force

  メディアアート/イベント展示など、見ただけでは正体が分からない被写体は
  プロファイルと文脈を指定すると精度が上がる:
    python image_indexer.py <folder> --profile art \\
        --context "Tokyo Lights 2026 Artpark のメディアアート展示"
"""

import argparse
import json
import os
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:
    import ollama
except ImportError:
    sys.exit("ollama パッケージが必要です:  pip install ollama")

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow パッケージが必要です:  pip install pillow")

# HEICは事前に .claude/scripts のImageMagickスクリプトでJPEG化しておく前提
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MANIFEST_NAME = "_manifest.json"

# 構造化JSONで返させるためのスキーマ（Ollamaの format パラメータに渡す）
SCHEMA = {
    "type": "object",
    "properties": {
        "caption":   {"type": "string"},
        "subject":   {"type": "string"},
        "scene":     {"type": "string"},
        "ocr_text":  {"type": "string"},
        "tags":      {"type": "array", "items": {"type": "string"}},
        "slug_hint": {"type": "string"},
    },
    "required": ["caption", "subject", "scene", "ocr_text", "tags", "slug_hint"],
}

# 汎用: 見た目＝正体が一致する被写体（聖地巡礼スポット、食事、物販など）向け
PROMPT_GENERAL = """この写真をブログ記事用に分析し、日本語で記述してください。
- caption: この写真が何を写しているかを1〜2文で説明
- subject: 主な被写体（例: キーボード自作展示、神社の鳥居、ラーメン）
- scene: 場所やシーン（例: 屋内の展示ブース、海沿いの道、店内のテーブル席）
- ocr_text: 画像内に読み取れる文字（看板・作品名・価格表示・案内板など）。なければ空文字
- tags: 検索用の日本語キーワードを3〜6個
- slug_hint: ファイル名に使える英小文字ハイフン区切りの短い語（例: makerfaire-keyboard, torii-gate）
事実だけを記述し、写っていないものを推測で足さないこと。"""

# アート用: 正体（作品名・作家）は画面外情報なので推測させず、視覚描写とOCRに徹する
PROMPT_ART = """この写真はメディアアート/現代アートの展示作品です。日本語で記述してください。
重要: 作品名や作家名を推測で断定しないこと。見えていないコンセプトを補わないこと。
- caption: 鑑賞者が体験する光景を視覚的に描写（光・色・映像・動き・空間・規模・観客の様子）
- subject: 表現の形態のみ（例: プロジェクションマッピング, LEDインスタレーション, 映像作品, 立体造形, インタラクティブ展示）。作品名ではない
- scene: 展示空間（例: 暗室, 屋外広場, ギャラリーの壁面, 体験型ブース）
- ocr_text: キャプションプレート・看板の文字（作品名・作家名・解説）を正確に書き写す。文字が無ければ空文字
- tags: 視覚的特徴の日本語キーワード3〜6個（色・モチーフ・技法など）
- slug_hint: 英小文字ハイフン区切りの短い語。プレートから作品名が読めればそれ、無ければ視覚特徴ベース
作品名・作家名は ocr_text に文字がある場合のみ記載すること。"""

PROMPTS = {"general": PROMPT_GENERAL, "art": PROMPT_ART}


def build_prompt(profile: str, context: str) -> str:
    base = PROMPTS[profile]
    if context:
        return f"【前提となる文脈】{context}\n（この文脈は参考情報。写っている事実と矛盾する場合は写っている方を優先）\n\n{base}"
    return base


RESIZE_MAX_SIDE = 1024  # この長辺を超える画像のみ縮小（解析精度はモデル側の入力解像度で頭打ちのため十分）


@contextmanager
def resized_for_analysis(path: Path):
    """長辺がRESIZE_MAX_SIDEを超える画像だけ一時ファイルに縮小する。使用後は自動削除。"""
    with Image.open(path) as img:
        if max(img.size) <= RESIZE_MAX_SIDE:
            yield path
            return
        img = img.convert("RGB")
        img.thumbnail((RESIZE_MAX_SIDE, RESIZE_MAX_SIDE), Image.LANCZOS)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()
        try:
            img.save(tmp_path, "JPEG", quality=85)
            yield tmp_path
        finally:
            tmp_path.unlink(missing_ok=True)


def analyze_image(path: Path, model: str, prompt: str, host: str | None,
                  num_ctx: int, attempts: int = 2) -> dict:
    client = ollama.Client(host=host) if host else ollama
    last_err: Exception | None = None
    with resized_for_analysis(path) as send_path:
        for _ in range(attempts):
            resp = client.chat(
                model=model,
                messages=[{"role": "user", "content": prompt, "images": [str(send_path)]}],
                format=SCHEMA,
                think=False,  # 構造化抽出に思考は不要。思考側にトークンを使い切る空応答も防ぐ
                # num_ctx を明示しないとOllama既定の4096に絞られ、画像のトークンで溢れる
                options={"temperature": 0.2, "num_ctx": num_ctx},
            )
            content = (resp["message"].get("content") or "").strip()
            if not content:
                last_err = ValueError("モデルが空応答を返しました")
                continue
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                last_err = e  # 非JSON応答。サンプリングのゆらぎなら再試行で通ることが多い
    raise RuntimeError(f"有効なJSONを取得できませんでした: {last_err}")


def load_manifest(folder: Path) -> dict:
    mf = folder / MANIFEST_NAME
    if mf.exists():
        try:
            return json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  ! 既存の {MANIFEST_NAME} が壊れています。新規生成します。")
    return {}


def save_manifest(folder: Path, data: dict) -> None:
    mf = folder / MANIFEST_NAME
    # BOMなしUTF-8で書き出す（reve-writerパイプラインの方針に合わせる）
    mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="reve-writer 写真索引ジェネレータ (Qwen3-VL/Ollama)")
    ap.add_argument("folder", help="解析対象の画像フォルダ（NASパス可）")
    ap.add_argument("--model", default="qwen3-vl:8b", help="Ollamaモデル名（既定: qwen3-vl:8b）")
    ap.add_argument("--profile", choices=["general", "art"], default="general",
                    help="プロンプトの種類。art=メディアアート/展示向け（既定: general）")
    ap.add_argument("--context", default="",
                    help="被写体の前提文脈。例: 'Tokyo Lights 2026 のメディアアート展示'")
    ap.add_argument("--host", default=None, help="Ollamaホスト（既定: http://localhost:11434）")
    ap.add_argument("--num-ctx", type=int, default=8192,
                    help="コンテキスト窓のトークン数（既定: 8192）。溢れるなら16384等に上げる")
    ap.add_argument("--force", action="store_true", help="索引済みの写真も再解析する")
    ap.add_argument("--workers", type=int, default=1,
                    help="並列処理数（既定: 1=直列）。Ollamaの OLLAMA_NUM_PARALLEL と合わせること")
    ap.add_argument("--files", nargs="+", metavar="FILE",
                    help="解析するファイル名を指定（省略時はフォルダ内全ファイル）")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"フォルダが見つかりません: {folder}")

    if args.files:
        images = []
        for name in args.files:
            p = folder / name
            if not p.exists():
                print(f"  ! ファイルが見つかりません: {name}")
            elif p.suffix.lower() not in IMAGE_EXTS:
                print(f"  ! 対応していない形式です: {name}")
            else:
                images.append(p)
        images = sorted(images)
    else:
        images = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        sys.exit(f"対象画像がありません: {folder}")

    prompt = build_prompt(args.profile, args.context.strip())
    manifest = load_manifest(folder)
    manifest_lock = threading.Lock()
    total = len(images)
    done = skipped = failed = 0

    if args.workers > 1:
        num_parallel = int(os.environ.get("OLLAMA_NUM_PARALLEL", "1"))
        if num_parallel < args.workers:
            print(f"  警告: OLLAMA_NUM_PARALLEL={num_parallel} が --workers {args.workers} より小さいです。")
            print(f"         並列効果が出ません。以下を実行後にOllamaを再起動してください:")
            print(f'         [System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "{args.workers}", "User")')

    print(f"対象 {total} 枚 / モデル {args.model} / プロファイル {args.profile} / 並列数 {args.workers}")
    if args.context.strip():
        print(f"文脈: {args.context.strip()}")

    targets = []
    for img in images:
        if not args.force and img.name in manifest:
            skipped += 1
        else:
            targets.append(img)

    if skipped:
        print(f"  スキップ（索引済み）: {skipped} 枚")

    def process(img: Path) -> tuple[str, dict | None, Exception | None]:
        try:
            result = analyze_image(img, args.model, prompt, args.host, args.num_ctx)
            result["file"] = img.name
            result["profile"] = args.profile
            result["indexed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            return img.name, result, None
        except Exception as e:  # noqa: BLE001
            return img.name, None, e

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process, img): img for img in targets}
        for future in as_completed(futures):
            key, result, err = future.result()
            if err:
                failed += 1
                print(f"  NG {key} ({err})")
            else:
                done += 1
                print(f"  OK {key}")
                with manifest_lock:
                    manifest[key] = result
                    save_manifest(folder, manifest)  # 1枚ごとに保存（中断しても進捗は残る）

    save_manifest(folder, manifest)
    print(f"\n完了: 解析 {done} / スキップ {skipped} / 失敗 {failed}")
    print(f"出力: {folder / MANIFEST_NAME}")


if __name__ == "__main__":
    main()