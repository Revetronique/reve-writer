#!/usr/bin/env bash
#
# HEIC画像をJPEGに変換する。OSを自動判定して以下を使い分ける:
#   - macOS:   標準コマンド `sips`
#   - Windows: PowerShell + WIC（HEIF画像拡張機能が必要）
# 単一ファイルまたはフォルダ内の全HEICファイルを一括変換する。
#
# 前提:
#   - Windows: Microsoft Store の「HEIF 画像拡張機能」がインストール済みであること
#     （未インストールの場合は ms-windows-store://pdp/?productid=9pmmsr1cgpwg ）
#   - macOS: 標準搭載の `sips` を使用（追加インストール不要）
#
# 使い方:
#   ./convert-heic-to-jpeg.sh <ファイルまたはフォルダのパス>
#
# 例:
#   ./convert-heic-to-jpeg.sh /y/Event/2026-06-makerfaire/photo.HEIC
#   ./convert-heic-to-jpeg.sh "/y/Event/2026-06-makerfaire/"

set -euo pipefail

TARGET="${1:-}"

if [ -z "$TARGET" ]; then
    echo "使い方: $0 <ファイルまたはフォルダのパス>" >&2
    exit 1
fi

convert_macos() {
    if [ -f "$TARGET" ]; then
        local output="${TARGET%.HEIC}.jpg"
        output="${output%.heic}.jpg"
        sips -s format jpeg "$TARGET" -o "$output"
        echo "変換完了: $output"
    elif [ -d "$TARGET" ]; then
        local found=0
        for file in "$TARGET"/*.HEIC "$TARGET"/*.heic; do
            [ -e "$file" ] || continue
            found=1
            local output="${file%.HEIC}.jpg"
            output="${output%.heic}.jpg"
            sips -s format jpeg "$file" -o "$output"
            echo "変換完了: $output"
        done
        if [ "$found" -eq 0 ]; then
            echo "HEICファイルが見つかりませんでした。"
        fi
    else
        echo "パスが見つかりません: $TARGET" >&2
        exit 1
    fi
}

convert_windows() {
# Git Bashのパスのまま渡さず、PowerShell側にWindows形式に変換して渡す
WIN_TARGET="$(cygpath -w "$TARGET" 2>/dev/null || echo "$TARGET")"

powershell.exe -NoProfile -NonInteractive -Command "
Add-Type -AssemblyName PresentationCore

function Convert-HeicToJpeg(\$inputPath, \$outputPath) {
    \$uri = New-Object System.Uri(\$inputPath)
    \$decoder = [System.Windows.Media.Imaging.BitmapDecoder]::Create(
        \$uri, [System.Windows.Media.Imaging.BitmapCreateOptions]::None,
        [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad)
    \$encoder = New-Object System.Windows.Media.Imaging.JpegBitmapEncoder
    \$encoder.Frames.Add(\$decoder.Frames[0])
    \$stream = [System.IO.File]::Create(\$outputPath)
    \$encoder.Save(\$stream)
    \$stream.Close()
}

\$target = '$WIN_TARGET'

if (Test-Path \$target -PathType Leaf) {
    \$outputPath = \$target -replace '\.HEIC$', '.jpg'
    Convert-HeicToJpeg \$target \$outputPath
    Write-Output \"変換完了: \$outputPath\"
} elseif (Test-Path \$target -PathType Container) {
    \$files = Get-ChildItem -Path \$target -Filter *.HEIC
    if (\$files.Count -eq 0) {
        Write-Output 'HEICファイルが見つかりませんでした。'
        exit 0
    }
    foreach (\$file in \$files) {
        \$outputPath = \$file.FullName -replace '\.HEIC$', '.jpg'
        try {
            Convert-HeicToJpeg \$file.FullName \$outputPath
            Write-Output \"変換完了: \$outputPath\"
        } catch {
            Write-Output \"失敗: \$(\$file.FullName) - \$(\$_.Exception.Message)\"
        }
    }
} else {
    Write-Output \"パスが見つかりません: \$target\"
    exit 1
}
"
}

case "$(uname -s)" in
    Darwin)
        convert_macos
        ;;
    *)
        convert_windows
        ;;
esac
