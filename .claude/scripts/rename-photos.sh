#!/usr/bin/env bash
#
# フォルダ内の画像ファイルをCLAUDE.mdの命名規則に従って一括リネームする。
#   形式: YYYYMMDD-{slug}-{NNNN}.jpg（連番4桁、既存ファイルと重複しないよう採番）
#
# 使い方:
#   ./rename-photos.sh <フォルダパス> <YYYYMMDD> <slug>
#
# 例:
#   ./rename-photos.sh /y/Event/2026-06-makerfaire/ 20260601 makerfaire-tokyo-2026
#   → 20260601-makerfaire-tokyo-2026-0001.jpg, 0002.jpg, ...
#
# 対象拡張子: jpg, jpeg, png, webp（大文字小文字区別なし）
# 既にYYYYMMDD-slug-NNNN形式のファイルがフォルダにある場合は、その最大連番の続きから採番する。

set -euo pipefail

FOLDER="${1:-}"
DATE="${2:-}"
SLUG="${3:-}"

if [ -z "$FOLDER" ] || [ -z "$DATE" ] || [ -z "$SLUG" ]; then
    echo "使い方: $0 <フォルダパス> <YYYYMMDD> <slug>" >&2
    exit 1
fi

if [ ! -d "$FOLDER" ]; then
    echo "フォルダが見つかりません: $FOLDER" >&2
    exit 1
fi

if ! [[ "$DATE" =~ ^[0-9]{8}$ ]]; then
    echo "日付はYYYYMMDD形式で指定してください: $DATE" >&2
    exit 1
fi

# フォルダ末尾のスラッシュを除去
FOLDER="${FOLDER%/}"

# 既存の同名パターン（DATE-SLUG-NNNN.ext）から最大連番を取得し、その続きから採番する
max_existing=0
for f in "$FOLDER"/"$DATE"-"$SLUG"-[0-9][0-9][0-9][0-9].*; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    num="${base#"$DATE"-"$SLUG"-}"
    num="${num%%.*}"
    if [[ "$num" =~ ^[0-9]{4}$ ]]; then
        num=$((10#$num))
        if [ "$num" -gt "$max_existing" ]; then
            max_existing=$num
        fi
    fi
done

counter=$((max_existing + 1))
renamed=0

# 対象画像をファイル名順に収集（リネーム済みファイルは除外）
shopt -s nullglob nocaseglob
files=()
for f in "$FOLDER"/*.jpg "$FOLDER"/*.jpeg "$FOLDER"/*.png "$FOLDER"/*.webp; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    if [[ "$base" =~ ^${DATE}-${SLUG}-[0-9]{4}\. ]]; then
        continue
    fi
    files+=("$f")
done
shopt -u nullglob nocaseglob

if [ "${#files[@]}" -eq 0 ]; then
    echo "リネーム対象の画像が見つかりませんでした。"
    exit 0
fi

IFS=$'\n' files=($(printf '%s\n' "${files[@]}" | sort))
unset IFS

for f in "${files[@]}"; do
    ext="${f##*.}"
    ext="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
    num=$(printf "%04d" "$counter")
    newname="${DATE}-${SLUG}-${num}.${ext}"
    newpath="$FOLDER/$newname"

    if [ -e "$newpath" ]; then
        echo "スキップ（既存ファイルと衝突）: $newname" >&2
        continue
    fi

    mv "$f" "$newpath"
    echo "$(basename "$f") -> $newname"

    counter=$((counter + 1))
    renamed=$((renamed + 1))
done

echo "リネーム完了: ${renamed} 枚"
