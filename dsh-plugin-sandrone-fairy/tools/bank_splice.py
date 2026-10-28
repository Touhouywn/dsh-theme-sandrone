"""拼接式可行性的第二个指标：把一句话切成「语料里原样存在的片段」，看需要几刀。"""

import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

lines = []
with io.open(os.path.join(ROOT, "tts", "dataset", "list.txt"), encoding="utf-8") as fh:
    for row in fh:
        parts = row.strip().split("|")
        if len(parts) >= 4:
            clean = re.sub(r"[^\u4e00-\u9fff]", "", parts[3])
            if clean:
                lines.append(clean)
corpus = "\u0001".join(lines)

pack = json.loads(io.open(os.path.join(ROOT, "tts", "pack.json"), encoding="utf-8").read())
tests = list(pack.values()) + [
    "先别急着决定。我得知道一件事：这个项目是在磨你，还是在耗你。",
    "我推演过了，三条路里只有一条不需要你熬夜。",
    "把茶端稳。慌的时候手会抖。",
    "别把「做不到」和「不想做」混在一起。",
    "雪，慢一点。你已经跑了很久了。",
]


def split_by_corpus(sentence, min_len=2):
    """贪心取语料里最长的匹配片段。"""
    text = re.sub(r"[^\u4e00-\u9fff]", "", sentence)
    pieces, i, misses = [], 0, 0
    while i < len(text):
        best, best_len = None, 0
        for length in range(len(text) - i, min_len - 1, -1):
            chunk = text[i:i + length]
            if chunk in corpus:
                best, best_len = chunk, length
                break
        if best:
            pieces.append(best)
            i += best_len
        else:
            pieces.append(text[i])
            misses += 1
            i += 1
    return pieces, misses


print("%-34s %6s %6s %s" % ("句子", "片段数", "单字", "最长片段"))
all_pieces, all_misses = [], 0
for s in tests:
    pieces, miss = split_by_corpus(s)
    all_pieces.append(len(pieces))
    all_misses += miss
    longest = max(pieces, key=len) if pieces else ""
    print("%-34s %6d %6d %s" % (s[:16] + "…" + s[-8:] if len(s) > 26 else s,
                                len(pieces), miss, longest))

avg_chars = sum(len(re.sub(r"[^\u4e00-\u9fff]", "", s)) for s in tests) / float(len(tests))
print()
print("平均每句 %.1f 字 → 平均 %.1f 个片段（每片段 %.2f 字）" % (
    avg_chars, sum(all_pieces) / float(len(all_pieces)),
    avg_chars / (sum(all_pieces) / float(len(all_pieces)))))
print("单字兜底总数:", all_misses)
