#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# scaffold-deck.sh — 一键创建 xhs 卡组工作区（deck 形态，非文章形态）。
#
# 用法：
#   bash scripts/scaffold-deck.sh <run-dir> --theme=<id>   （--theme 必填：主题是用户决策，无静默默认）
#   bash scripts/scaffold-deck.sh --list-themes
#
# 工作区生来就是 Deck/Card/cards 结构，index.html 已按主题加载字体。
# reacticle 从 npm 安装最新发布版。
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$SKILL_DIR/assets/deck-template"

# ── 主题 → Google Fonts 链接（商业字体栈用可得回退；tufte 用系统字体）──
fonts_for() {
  case "$1" in
    andy)     echo 'https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=Nunito:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    bayer)    echo 'https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@400;500;600;700&family=Poppins:wght@400;500;600;700&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    bodoni)   echo 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800;900&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    freddie)  echo 'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Hanken+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    fuller)   echo 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    knuth)    echo 'https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    press)    echo 'https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Source+Serif+4:opsz,wght@8..60,400&family=Spectral:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    shannon)  echo 'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap' ;;
    sottsass) echo 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap' ;;
    tufte)    echo '(tufte 使用系统字体栈，无需 webfont)' ;;
    vignelli) echo 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap' ;;
    *) return 1 ;;
  esac
}

list_themes() {
  echo "可用主题：andy freddie sottsass bayer press tufte shannon vignelli knuth bodoni fuller"
  echo "选型指引见 references/themes.md（内容契合优先）。"
}

# ── 解析参数 ──
TARGET=""; THEME=""
for arg in "$@"; do
  case "$arg" in
    --list-themes) list_themes; exit 0 ;;
    --theme=*) THEME="${arg#--theme=}" ;;
    --*) echo "✗ 未知参数: $arg" >&2; exit 1 ;;
    *) [[ -z "$TARGET" ]] && TARGET="$arg" ;;
  esac
done
TARGET="${TARGET:-xhs-deck}"
[[ -n "$THEME" ]] || { echo "✗ 需要 --theme=<id>（主题必须显式选定）" >&2; list_themes >&2; exit 1; }

FONTS="$(fonts_for "$THEME")" || { echo "✗ 未知主题 '$THEME'" >&2; list_themes >&2; exit 1; }

# 目录检查：允许已含记忆目录（source/ plan/ preview/ exports/）的 run-dir
# （管线先写 source/plan 再脚手架）；只拦工程文件冲突。
if [[ -f "$TARGET/package.json" || -d "$TARGET/article" ]]; then
  echo "✗ '$TARGET' 已有 deck 工程文件（package.json/article），疑似重复脚手架，已中止。" >&2; exit 1
fi
command -v npm >/dev/null || { echo "✗ 需要 npm。" >&2; exit 1; }

echo "▸ 创建卡组工作区：$TARGET（主题 $THEME）"
mkdir -p "$TARGET"
cp "$TEMPLATE/package.json"      "$TARGET/package.json"
cp "$TEMPLATE/vite.config.ts"    "$TARGET/vite.config.ts"
cp "$TEMPLATE/tsconfig.json"     "$TARGET/tsconfig.json"
cp "$TEMPLATE/index.html"        "$TARGET/index.html"
mkdir -p "$TARGET/article/cards" "$TARGET/article/assets" \
         "$TARGET/source" "$TARGET/plan" "$TARGET/preview" "$TARGET/exports"
cp "$TEMPLATE/article/main.tsx"          "$TARGET/article/main.tsx"
cp "$TEMPLATE/article/Deck.tsx"          "$TARGET/article/Deck.tsx"
cp "$TEMPLATE/article/Card.tsx"          "$TARGET/article/Card.tsx"
cp "$TEMPLATE/article/vite-env.d.ts"     "$TARGET/article/vite-env.d.ts"
cp "$TEMPLATE/article/cards/_shared.tsx" "$TARGET/article/cards/_shared.tsx"
cp "$TEMPLATE/article/cards/01-cover.tsx" "$TARGET/article/cards/01-cover.tsx"
touch "$TARGET/article/assets/.gitkeep"

# ── 注入主题 id 与字体链接 ──
export RA_THEME="$THEME" RA_FONTS="$FONTS"
perl -pi -e 's/__THEME__/$ENV{RA_THEME}/g' "$TARGET/article/main.tsx"
if [[ "$THEME" == "tufte" ]]; then
  perl -pi -e 's{^\s*__FONTS__.*\n}{}' "$TARGET/index.html"
else
  perl -pi -e 's{__FONTS__}{<link rel="preconnect" href="https://fonts.googleapis.com" />\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n    <link href="$ENV{RA_FONTS}" rel="stylesheet" />}' "$TARGET/index.html"
fi

echo "▸ npm install（reacticle 最新版）"
(cd "$TARGET" && npm install --silent)

cat <<EOF

✓ 工作区就绪：$TARGET
  下一步：读 references/card-anatomy.md + typography.md，设计全部卡片；
  验证：node <skill>/scripts/verify.mjs $TARGET
  渲染：node <skill>/scripts/export-png.mjs $TARGET
EOF
