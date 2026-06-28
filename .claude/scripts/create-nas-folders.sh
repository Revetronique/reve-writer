#!/usr/bin/env bash
#
# NAS上にLoveLiveのグループ別フォルダ構成を一括作成する。
# Y:\LoveLive\{グループ名}\{Live,Exhibition,Travel} を作成する（既存フォルダはスキップ）。
#
# 使い方:
#   ./create-nas-folders.sh [ROOT]
#   ROOT 省略時は /y（Git Bashから見た Y:\）

set -euo pipefail

ROOT="${1:-/y}"

GROUPS=("Muse" "Aqours" "Nijigasaki" "Liella" "Hasunosora" "Bluebird" "Musical" "Yohane")
SUBS=("Live" "Exhibition" "Travel")

LOVELIVE_ROOT="$ROOT/LoveLive"

for group in "${GROUPS[@]}"; do
    for sub in "${SUBS[@]}"; do
        mkdir -p "$LOVELIVE_ROOT/$group/$sub"
    done
done

find "$LOVELIVE_ROOT" -type d
