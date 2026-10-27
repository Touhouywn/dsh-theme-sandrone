"""日语归一（04 对齐与 05 审计共用这一份实现）。

口径（见 ops/04-align.md §归一）：
  1. NFKC；
  2. 只保留 平假名/片假名/汉字/英数 [\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]；
  3. 片假名 U+30A1..U+30F6 统一减 0x60 折成平假名；长音符「ー」丢弃。

注意：filter 放在折字之前也一样——折字只动假名区，不动汉字/英数。
"""

from __future__ import annotations

import re
import unicodedata

KEEP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]")
LONG_VOWEL = "\u30fc"  # ー


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = "".join(KEEP.findall(text))
    out = []
    for ch in text:
        if ch == LONG_VOWEL:
            continue
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def grams(s: str) -> set[str]:
    if not s:
        return set()
    if len(s) == 1:
        return {s}
    return {s[i:i + 2] for i in range(len(s) - 1)}


def dice(a: str, b: str) -> float:
    """2-gram Dice（与 v2 同公式）。入参应已 norm。"""
    if not a or not b:
        return 0.0
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return 2 * len(ga & gb) / (len(ga) + len(gb))


def threshold(norm_text: str) -> float:
    """短行（≤12 字）0.45；长行 0.42。"""
    return 0.45 if len(norm_text) <= 12 else 0.42
