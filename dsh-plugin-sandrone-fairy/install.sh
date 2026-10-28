#!/usr/bin/env bash
# Sandrone · 机偶 —— 安装脚本（Linux / macOS）
#
# 做的事和 install.ps1 一样：
#   1. 复制到 $DSH_HOME/plugins/sandrone-fairy
#   2. 在 profile 的 node_modules 建软链
#   3. 幂等追加 cordis.patch.yml 的 insert 行
#   4. 剥掉 UTF-8 BOM（DSH 启动时对 BOM 是 fatal）
#
# 用法：
#   bash ./install.sh                       # 默认 profile
#   bash ./install.sh --profile desktop     # 指定 profile
#   bash ./install.sh --dsh-home ~/.dsh     # 指定 DSH_HOME
#   bash ./install.sh --purge               # 卸载（保留已下载的模型）

set -euo pipefail

NAME="sandrone-fairy"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PROFILE="${DSH_PROFILE:-}"
PURGE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --dsh-home) DSH_HOME="$2"; shift 2 ;;
    --purge) PURGE=1; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$PROFILE" ]; then
  if [ -d "$DSH_HOME/profiles/desktop" ]; then PROFILE="desktop"; else
    PROFILE="$(ls -1 "$DSH_HOME/profiles" 2>/dev/null | head -n1 || true)"
  fi
fi
[ -n "$PROFILE" ] || { echo "找不到 profile，请用 --profile 指定" >&2; exit 1; }

PROFILE_DIR="$DSH_HOME/profiles/$PROFILE"
PATCH="$PROFILE_DIR/cordis.patch.yml"
DEST="$DSH_HOME/plugins/$NAME"
LINK="$PROFILE_DIR/node_modules/$NAME"

echo "DSH_HOME = $DSH_HOME"
echo "profile  = $PROFILE"

if [ "$PURGE" = "1" ]; then
  [ -L "$LINK" ] && rm -f "$LINK" && echo "removed link"
  if [ -f "$PATCH" ]; then
    cp "$PATCH" "$PATCH.bak-$(date +%Y%m%d%H%M%S)"
    grep -v "id: $NAME" "$PATCH" > "$PATCH.tmp" && mv "$PATCH.tmp" "$PATCH"
    echo "removed pacth row (backup kept)"
  fi
  echo "卸载完成；$DEST 下的文件与已下载模型保留，需要彻底删除请手动 rm -rf \"$DEST\""
  exit 0
fi

mkdir -p "$DSH_HOME/plugins" "$PROFILE_DIR/node_modules"
rm -rf "$DEST"
mkdir -p "$DEST"
for item in index.js client.js cordis.patch.yml icon.svg package.json \
            locale assets tts ui tools docs README.md CHANGELOG.md NOTICE.md LICENSE INTEGRATION.md; do
  [ -e "$SRC/$item" ] && cp -R "$SRC/$item" "$DEST/"
done
# 不要带开发产物
rm -rf "$DEST/tts/gptsovits" "$DEST/tts/dataset" "$DEST/tts/dataset2" "$DEST/tts/dataset_old" \
       "$DEST/tts/rvc" "$DEST/tts/rvcenv" "$DEST/assets/voice/cache" "$DEST/data"
echo "copied -> $DEST"

rm -f "$LINK"
ln -s "$DEST" "$LINK"
echo "linked  -> $LINK"

if [ -f "$PATCH" ]; then
  if grep -q "id: $NAME" "$PATCH"; then
    echo "patch row already present"
  else
    printf '\n- insert:\n    - id: %s\n      name: %s\n' "$NAME" "$NAME" >> "$PATCH"
    echo "patch row appended"
  fi
else
  printf -- '- insert:\n    - id: %s\n      name: %s\n' "$NAME" "$NAME" > "$PATCH"
  echo "patch file created"
fi

# 剥 BOM
if head -c 3 "$PATCH" | grep -q $'\xef\xbb\xbf'; then
  tail -c +4 "$PATCH" > "$PATCH.nobom" && mv "$PATCH.nobom" "$PATCH"
  echo "bom stripped"
fi

echo
echo "装好了。下一步："
echo "  1. 刷新浏览器页面"
echo "  2. 打开 /sandrone/setup 按提示补语音引擎（首次约 2 GB 依赖 + 1.28 GB 底座模型）"
