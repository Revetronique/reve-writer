#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image_indexer.py  —  reve-writer 写真索引ジェネレータ

NASフォルダ内の画像をローカル Qwen3-VL (Ollama) で解析し、
フォルダ直下に `_manifest.json` を生成する。

reve-writer (Claude.ai) はこの manifest を読み、下書きの
`[★写真: {{説明}}]` プレースホルダに最適な写真を割り当てる。
マッチング自体はテキスト対テキストなので Claude.ai が担当する。
本スクリプトの役割は「画像の中身をテキスト化する」ところまで。

前提:
    pip install ollama
    ollama pull qwen3-vl:8b        # VRAM 8GBなら qwen3-vl:4b
    ollama serve  (通常は自動起動)

使い方:
    python image_indexer.py "Y:\\photos\\events\\2026-06-makerfaire"
    python image_indexer.py <folder> --model qwen3-vl:4b --force
"""

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import ollama
except ImportError:
    sys.exit("ollama パッケージが必要です:  pip install ollama")

# HEICは事前に .claude/scripts のImageMagickスクリプトでJPEG化しておく前提
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MANIFEST_NAME = "_manifest.json"

# Qwen3-VLに構造化JSONで返させるためのスキーマ（Ollamaの format パラメータに渡す）
SCHEMA = {
    "type": "object",
    "properties": {
        "caption":   {"type": "string"},          # 1〜2文の日本語説明
        "subject":   {"type": "string"},           # 主な被写体
        "scene":     {"type": "string"},           # 場所・シーン（屋内/屋外、展示ブース等）
        "ocr_text":  {"type": "string"},           # 画像内の文字（看板・作品名・価格等）。無ければ""
        "tags":      {"type": "array", "items": {"type": "string"}},  # 日本語キーワード
        "slug_hint": {"type": "string"},           # ファイル名向けの英小文字スラッグ案
    },
    "required": ["caption", "subject", "scene", "ocr_text", "tags", "slug_hint"],
}

PROMPT = """この写真をブログ記事用に分析し、日本語で記述してください。
- caption: この写真が何を写しているかを1〜2文で説明
- subject: 主な被写体（例: キーボード自作展示、神社の鳥居、ラーメン）
- scene: 場所やシーン（例: 屋内の展示ブース、海沿いの道、店内のテーブル席）
- ocr_text: 画像内に読み取れる文字（看板・作品名・価格表示・案内板など）。なければ空文字
- tags: 検索用の日本語キーワードを3〜6個
- slug_hint: ファイル名に使える英小文字ハイフン区切りの短い語（例: makerfaire-keyboard, torii-gate）
事実だけを記述し、写っていないものを推測で足さないこと。"""


def analyze_image(path: Path, model: str, host: str | None) -> dict:
    """1枚の画像をQwen3-VLに解析させ、構造化dictを返す。"""
    client = ollama.Client(host=host) if host else ollama
    resp = client.chat(
        model=model,
        messages=[{"role": "user", "content": PROMPT, "images": [str(path)]}],
        format=SCHEMA,
        options={"temperature": 0.2},  # 説明文の安定性を優先
    )
    raw = resp["message"]["content"]
    return json.loads(raw)


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
    mf.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="reve-writer 写真索引ジェネレータ (Qwen3-VL/Ollama)")
    ap.add_argument("folder", help="解析対象の画像フォルダ（NASパス可）")
    ap.add_argument("--model", default="qwen3-vl:8b", help="Ollamaモデル名（既定: qwen3-vl:8b）")
    ap.add_argument("--host", default=None, help="Ollamaホスト（既定: http://localhost:11434）")
    ap.add_argument("--force", action="store_true", help="索引済みの写真も再解析する")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"フォルダが見つかりません: {folder}")

    images = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        sys.exit(f"対象画像がありません: {folder}")

    manifest = load_manifest(folder)
    total = len(images)
    done = skipped = failed = 0

    print(f"対象 {total} 枚 / モデル {args.model}")
    for i, img in enumerate(images, 1):
        key = img.name
        if not args.force and key in manifest:
            skipped += 1
            continue
        print(f"  [{i}/{total}] {key} ... ", end="", flush=True)
        try:
            result = analyze_image(img, args.model, args.host)
            result["file"] = key
            result["indexed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            manifest[key] = result
            done += 1
            print("OK")
            # 1枚ごとに保存しておけば途中で止めても進捗は残る
            save_manifest(folder, manifest)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"NG ({e})")

    save_manifest(folder, manifest)
    print(f"\n完了: 解析 {done} / スキップ {skipped} / 失敗 {failed}")
    print(f"出力: {folder / MANIFEST_NAME}")


if __name__ == "__main__":
    main()