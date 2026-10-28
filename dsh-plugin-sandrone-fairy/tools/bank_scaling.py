"""语料放大后的拼接覆盖率曲线：语料越多，一句话能切成几个片段。"""

import io
import json
import os
import random
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

rows = []
with io.open(os.path.join(ROOT, "tts", "dataset", "list.txt"), encoding="utf-8") as fh:
    for line in fh:
        parts = line.strip().split("|")
        if len(parts) >= 4:
            clean = re.sub(r"[^\u4e00-\u9fff]", "", parts[3])
            if clean:
                rows.append(clean)

pack = json.loads(io.open(os.path.join(ROOT, "tts", "pack.json"), encoding="utf-8").read())
tests = [re.sub(r"[^\u4e00-\u9fff]", "", s) for s in pack.values()]
tests = [t for t in tests if t][:20]


def avg_piece(corpus_text, tests):
    total_pieces = 0
    total_chars = 0
    for text in tests:
        i = 0
        pieces = 0
        while i < len(text):
            best = 0
            for length in range(min(8, len(text) - i), 1, -1):
                if text[i:i + length] in corpus_text:
                    best = length
                    break
            pieces += 1
            i += best if best else 1
        total_pieces += pieces
        total_chars += len(text)
    return total_chars / float(total_pieces)


random.seed(7)
print("%8s %10s %10s" % ("语料句数", "语料字数", "每片段字数"))
for n in (32, 64, 128):
    subset = rows[:n]
    corpus = "\u0001".join(subset)
    chars = sum(len(s) for s in subset)
    print("%8d %10d %10.2f" % (n, chars, avg_piece(corpus, tests)))

# 外推：把同一批语料复制 8 倍也不能增加 n-gram，只有新语料才行
big = "\u0001".join(rows * 8)
print("%8s %10d %10.2f   (重复 8 倍，n-gram 不变)" % ("重复×8", sum(len(s) for s in rows) * 8,
                                                    avg_piece(big, tests)))
