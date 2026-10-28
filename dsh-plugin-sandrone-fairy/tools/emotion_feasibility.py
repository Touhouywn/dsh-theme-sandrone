"""喜怒哀乐四类，我们手上的语料到底够不够？

两件事分开测：
  1. 文本能不能分出四类（用词表打分，看命中分布）；
  2. 音频里这四类的声学特征差多少（f0 均值/标准差、能量起伏、语速），
     差别小 → 换参考音也换不出情绪；差别大 → 值得做四个池子。
"""

import io
import json
import os
import re

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, "tts", "dataset", "list.txt")

LEXICON = {
    "喜": {
        "strong": ["不错", "很好", "当然", "愿意", "荣幸", "欢迎", "恭喜", "成功", "喜欢", "满意",
                   "很好", "有趣", "有意思", "厉害", "有趣"],
        "weak": ["呢", "呀", "哦", "吧"],
        "punct": ["！"],
    },
    "怒": {
        "strong": ["滚", "闭嘴", "愚蠢", "警告", "不要", "休想", "放肆", "无礼", "可恶", "混账",
                   "立刻", "给我", "够了", "可笑", "别过来", "退下", "住手"],
        "weak": ["哼", "啧", "竟然"],
        "punct": ["！？", "！！"],
    },
    "哀": {
        "strong": ["遗憾", "可惜", "离开", "消失", "最后", "再见", "告别", "对不起", "难过",
                   "孤单", "寂寞", "没有意义", "牺牲", "死亡", "死去", "失去"],
        "weak": ["唉", "罢了", "算了"],
        "punct": ["……"],
    },
    "乐": {
        "strong": ["哼", "才不", "猜", "秘密", "有趣", "逗", "哈哈", "玩笑", "调皮", "想得美",
                   "笨", " silly", "多管闲事", "嘻嘻"],
        "weak": ["啦", "咯", "嘛", "哦"],
        "punct": ["～", "~"],
    },
}
BASE = {"喜": 0.10, "怒": 0.10, "哀": 0.10, "乐": 0.10}


def score(text):
    out = {}
    for emo, table in LEXICON.items():
        s = BASE[emo]
        for w in table["strong"]:
            s += 0.35 if w and w in text else 0
        for w in table["weak"]:
            s += 0.08 if w in text else 0
        for p in table["punct"]:
            s += 0.15 if p in text else 0
        out[emo] = round(s, 3)
    best = max(out, key=out.get)
    return best, out


def prosody(path):
    audio, sr = sf.read(path, always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    peak = np.max(np.abs(audio)) or 1.0
    audio = audio / peak
    import librosa
    f0, _, _ = librosa.pyin(audio, fmin=70, fmax=420, sr=sr, frame_length=1024, hop_length=256)
    f0 = f0[np.isfinite(f0)]
    hop = int(0.02 * sr)
    frames = max(1, len(audio) // hop)
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(frames)])
    db = 20 * np.log10(rms + 1e-12)
    voiced = db > (np.percentile(db, 60) - 12)
    speech = float(voiced.mean())
    return {
        "dur": len(audio) / sr,
        "f0_mean": float(np.mean(f0)) if len(f0) else 0.0,
        "f0_std": float(np.std(f0)) if len(f0) else 0.0,
        "erg_std": float(np.std(db)),
        "speech": speech,
        "chars_per_s": None,
    }


def main():
    rows = [line.rstrip("\n").split("|") for line in io.open(LIST, encoding="utf-8") if line.strip()]
    buckets = {}
    for row in rows:
        path, text = row[0], row[-1]
        emo, _ = score(text)
        buckets.setdefault(emo, []).append((path, text))
    print("文本分档（128 条语料）：")
    for emo in ["喜", "怒", "哀", "乐", "其他"]:
        if emo in buckets:
            print(f"  {emo}: {len(buckets[emo])}")
    print()
    print(f"{'emo':<4}{'n':>4}{'总时长':>8}{'时长中位':>9}{'f0均值':>8}{'f0标准差':>9}{'能量标准差':>10}{'有声占比':>9}{'字/秒':>7}")
    for emo in ["喜", "怒", "哀", "乐"]:
        items = buckets.get(emo) or []
        if not items:
            print(f"{emo:<4}{0:>4}   —— 没有语料")
            continue
        stats = []
        for path, text in items:
            full = path if os.path.isabs(path) else os.path.join(ROOT, path.replace("/", os.sep))
            if not os.path.exists(full):
                continue
            st = prosody(full)
            st["cps"] = len(text) / max(0.2, st["dur"] * st["speech"])
            stats.append(st)
        if not stats:
            print(f"{emo:<4}  (音频缺失)")
            continue
        total = sum(s["dur"] for s in stats)
        print(f"{emo:<4}{len(stats):>4}{total:>7.1f}s"
              f"{np.median([s['dur'] for s in stats]):>8.2f}s"
              f"{np.mean([s['f0_mean'] for s in stats]):>8.1f}"
              f"{np.mean([s['f0_std'] for s in stats]):>9.1f}"
              f"{np.mean([s['erg_std'] for s in stats]):>10.2f}"
              f"{np.mean([s['speech'] for s in stats]):>9.2f}"
              f"{np.mean([s['cps'] for s in stats]):>7.2f}")


if __name__ == "__main__":
    main()
