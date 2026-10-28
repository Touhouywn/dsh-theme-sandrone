"""评估「裁剪原声做音库、按语义相似度挑句播放」的可行性。

输出：
  1. 语料规模（时长/字数/唯一字/唯一带调音节）
  2. 用典型回复句测「最近邻句子检索」的相似度分布
  3. 覆盖率：一句话里有多少字音库里根本没有
"""

import io
import json
import os
import re

import numpy as np
from pypinyin import lazy_pinyin, Style

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 语料：128 条带转写的数据集 ───────────────────────────────────────────
lines = []
with io.open(os.path.join(ROOT, "tts", "dataset", "list.txt"), encoding="utf-8") as fh:
    for row in fh:
        parts = row.strip().split("|")
        if len(parts) >= 4:
            lines.append(parts[3])
corpus = "".join(lines)
hanzi = re.findall(r"[\u4e00-\u9fff]", corpus)
uniq_hanzi = sorted(set(hanzi))

syl = []
for ch in uniq_hanzi:
    p = lazy_pinyin(ch, style=Style.TONE3, errors="ignore")
    if p:
        syl.extend(p)

print("语料句子数:", len(lines))
print("语料总字数:", len(hanzi))
print("唯一汉字:", len(uniq_hanzi))
print("唯一带调音节:", len(set(syl)))

# ── 待测句子：28 条预制台词 + 12 条典型回复 ──────────────────────────────
pack = json.loads(io.open(os.path.join(ROOT, "tts", "pack.json"), encoding="utf-8").read())
tests = list(pack.values()) + [
    "先别急着决定。我得知道一件事：这个项目是在磨你，还是在耗你。",
    "齿轮转着。我听见了——每一齿咬合都稳，这具机偶没在偷懒。",
    "我推演过了，三条路里只有一条不需要你熬夜。",
    "这个问题比看起来简单，只是因为你想得太久了。",
    "把茶端稳。慌的时候手会抖，手一抖就容易摔东西。",
    "你今天第三次叹气了。叹气不解决问题，坐下来。",
    "数据不会说谎，说谎的是想看某个结论的人。",
    "行，那就按你的节奏来。我在旁边，不催。",
    "这一版比上一版干净，但还差一口气。",
    "需要我拆一遍给你听吗？还是你只想有个人在旁边坐着。",
    "别把「做不到」和「不想做」混在一起，这两件事的解法完全相反。",
    "雪，慢一点。你已经跑了很久了。",
]


def bigrams(text):
    clean = re.sub(r"[^\u4e00-\u9fff]", "", text)
    return {clean[i:i + 2] for i in range(len(clean) - 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


corpus_bg = [(s, bigrams(s)) for s in lines]

best_scores = []
covered_syl = set(syl)
for text in tests:
    bg = bigrams(text)
    best, best_sent = 0.0, ""
    for sent, cbg in corpus_bg:
        sc = jaccard(bg, cbg)
        if sc > best:
            best, best_sent = sc, sent
    py = []
    for ch in re.findall(r"[\u4e00-\u9fff]", text):
        py.extend(lazy_pinyin(ch, style=Style.TONE3, errors="ignore"))
    miss = [s for s in py if s not in covered_syl]
    best_scores.append((text, best, best_sent, len(py), len(miss)))

scores = np.array([b for _, b, _, _, _ in best_scores])
miss_rate = np.array([m / float(n) if n else 0 for _, _, _, n, m in best_scores])
print()
print("最近邻相似度: 中位 %.3f / 均值 %.3f / 最高 %.3f / 最低 %.3f" % (
    np.median(scores), scores.mean(), scores.max(), scores.min()))
print("音节缺失比例: 中位 %.1f%% / 均值 %.1f%%" % (
    np.median(miss_rate) * 100, miss_rate.mean() * 100))
print("相似度 >=0.35 的句子数: %d / %d" % (int((scores >= 0.35).sum()), len(scores)))
print()
print("样例（前 6 条）:")
for text, sc, sent, n, miss in best_scores[:6]:
    print("  %.3f  缺 %.0f%%  %s" % (sc, 100.0 * miss / max(1, n), text[:24]))
    print("        ↳ %s" % sent[:26])
