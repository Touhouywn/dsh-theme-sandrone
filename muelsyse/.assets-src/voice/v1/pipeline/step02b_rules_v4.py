"""02b slice-rules（v2-rules-4）：人声轨 + 词边界 -> 句表。

输入 00-normalized/<源键>/source-vocals.wav 与 02-asr/<源键>.words.json，
产出 01-slices/<源键>/{segments.json, segments.tsv}。

参数（修正稿 §02）：
  最小静音 180ms；合并间隙 <200ms；强制断开 >600ms
  头部 clip_start = min(能量起点 - 50ms, 第一个词 start - 40ms)
  尾部 clip_end   = min(能量终点 + 40ms, 最后一个词 end + 60ms)
  词时间戳缺失 → 退到「±120ms 内能量谷 + 40ms」
  片长仍卡 0.4–10s

能量判据：帧 20ms / hop 10ms；有声 = 高于「本段 p50 - 28dB」且高于 -55dBFS。
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, NORMALIZED, SLICES, SOURCE_KEYS, read_json, write_json  # noqa: E402
import wordcut  # noqa: E402

RULES = {
    "version": "v2-rules-5",
    "frameMs": 20,
    "hopMs": 10,
    "silenceDb": -38.0,
    "breakMs": 200,        # 最小静音 200ms 才断
    "mergeMs": 250,        # 间隙 <250ms 视为同句
    "forceBreakMs": 1000,  # 超过 1000ms 强制断开
    "minDurS": 0.4,
    "maxDurS": 10.0,
    "medianFloorS": 1.0,   # 全源统一的段长中位数下限
    "p25FloorS": 0.6,      # 更低一档：防止「中位够、一堆碎片」
    "headPadMs": 50,
    "tailPadMs": 40,
    "wordHeadPadMs": 40,
    "wordTailPadMs": 60,
    "valleyMs": 120,
    "fadeInMs": 25,
    "fadeOutMs": 40,
}


def frame_db(wav_path: Path) -> list[float]:
    import numpy as np

    with wave.open(str(wav_path), "rb") as fh:
        rate = fh.getframerate()
        raw = fh.readframes(fh.getnframes())
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    frame = int(rate * RULES["frameMs"] / 1000)
    hop = int(rate * RULES["hopMs"] / 1000)
    count = max(0, (len(samples) - frame) // hop + 1)
    if count == 0:
        return []
    idx = np.arange(frame)[None, :] + hop * np.arange(count)[:, None]
    rms = np.sqrt((samples[idx] ** 2).mean(axis=1))
    return (20.0 * np.log10(rms + 1e-9)).tolist()


class Db:
    def __init__(self, db: list[float]):
        self.db = db
        self.hop = RULES["hopMs"]
        self.frame = RULES["frameMs"]

    def at(self, ms: float) -> float:
        i = int(ms // self.hop)
        return self.db[i] if 0 <= i < len(self.db) else -999.0

    def threshold(self, start: int, end: int) -> float:
        seg = [self.at(t) for t in range(start, end, self.hop)]
        if not seg:
            return -55.0
        seg_sorted = sorted(seg)
        p50 = seg_sorted[len(seg_sorted) // 2]
        return max(-55.0, p50 - 28.0)

    def runs(self, start: int, end: int) -> list[list[int]]:
        thr = self.threshold(start, end)
        i0 = max(0, start // self.hop)
        i1 = min(len(self.db), end // self.hop + 1)
        pause = max(1, RULES["breakMs"] // self.hop)
        runs, begin, idle = [], None, 0
        for i in range(i0, i1):
            if self.db[i] > thr:
                if begin is None:
                    begin = i
                idle = 0
            elif begin is not None:
                idle += 1
                if idle >= pause:
                    runs.append([begin * self.hop, (i - idle + 1) * self.hop + self.frame])
                    begin, idle = None, 0
        if begin is not None:
            runs.append([begin * self.hop, min(end, (i1 - 1) * self.hop + self.frame)])
        return runs

    def energy_bounds(self, start: int, end: int) -> tuple[int, int]:
        runs = self.runs(start, end)
        if not runs:
            return start, end
        return runs[0][0], runs[-1][1]

    def valley(self, center: int, radius: int) -> int:
        lo = max(0, center - radius)
        hi = min(len(self.db) - 1, center // self.hop + radius // self.hop)
        best, best_db = center, 1e9
        for i in range(lo // self.hop, hi + 1):
            mean = sum(self.db[max(0, i - 2):i + 3]) / 5
            if mean < best_db:
                best_db, best = mean, i * self.hop
        return best


def words_in(words: list[dict], start_ms: int, end_ms: int) -> list[dict]:
    lo = start_ms - 300
    hi = end_ms + 300
    return [w for w in words if w["start"] * 1000 >= lo and w["end"] * 1000 <= hi]


def resolve(frame: Db, raw: list[dict], words: list[dict]) -> tuple[list[dict], list[dict], dict]:
    min_ms = int(RULES["minDurS"] * 1000)
    max_ms = int(RULES["maxDurS"] * 1000)
    stats = {"decomposed": 0, "merged": 0, "headFromWord": 0, "tailFromWord": 0,
             "valleyFallback": 0, "tailTrimmedForOverlap": 0, "headPushedForOverlap": 0}

    pieces: list[dict] = []
    for block in raw:
        start, end = block["start"], block["end"]
        if end - start > max_ms:
            stats["decomposed"] += 1
            merged: list[dict] = []
            for lo, hi in frame.runs(start, end):
                # 间隙 <mergeMs 且并起来不超长 → 并成一句；≥forceBreakMs 一定是硬断
                if merged:
                    gap = lo - merged[-1]["end"]
                    if gap < RULES["mergeMs"] and hi - merged[-1]["start"] <= max_ms:
                        merged[-1]["end"] = hi
                        stats["merged"] += 1
                        continue
                merged.append({"start": lo, "end": hi})
            for seg in merged:
                lo, hi = seg["start"], seg["end"]
                while hi - lo > max_ms:
                    mid = frame.valley(lo + max_ms, RULES["valleyMs"])
                    pieces.append({"start": lo, "end": mid})
                    lo = mid
                pieces.append({"start": lo, "end": hi})
        else:
            pieces.append({"start": start, "end": end})

    kept, rejected = [], []
    for piece in sorted(pieces, key=lambda s: s["start"]):
        e_start, e_end = frame.energy_bounds(piece["start"], piece["end"])
        lw = wordcut.last_word_end(words, e_start, e_end)
        fw = wordcut.first_word_start(words, e_start, e_end)
        # 头尾各自独立判断：只要那一侧有词，就按词帽收；没有才退回能量谷
        if lw is not None:
            clip_end = min(e_end + RULES["tailPadMs"], lw + RULES["wordTailPadMs"])
            stats["tailFromWord"] += 1
        else:
            clip_end = frame.valley(e_end, RULES["valleyMs"]) + RULES["tailPadMs"]
            stats["valleyFallback"] += 1
        if fw is not None:
            clip_start = max(e_start - RULES["headPadMs"], fw - RULES["wordHeadPadMs"])
            stats["headFromWord"] += 1
        else:
            clip_start = frame.valley(e_start, RULES["valleyMs"]) - RULES["headPadMs"]
        seg = {"start": max(0, clip_start), "end": clip_end,
               "energyStart": e_start, "energyEnd": e_end}
        if seg["end"] - seg["start"] < min_ms:
            rejected.append({**seg, "reason": "too-short"})
            continue
        if seg["end"] - seg["start"] > max_ms:
            rejected.append({**seg, "reason": "too-long"})
            continue
        kept.append(seg)

    # 去重叠：先收上一段的尾巴，不要把这一段的头往前推——
    # 推头会把首字的起音削掉（实测「再见了」被削成「见了」）。
    final: list[dict] = []
    for seg in kept:
        if final and seg["start"] < final[-1]["end"]:
            if seg["start"] - final[-1]["start"] >= min_ms:
                final[-1]["end"] = seg["start"]
                stats["tailTrimmedForOverlap"] += 1
            else:
                seg["start"] = final[-1]["end"]
                stats["headPushedForOverlap"] += 1
        if seg["end"] - seg["start"] < min_ms:
            rejected.append({**seg, "reason": "too-short-after-merge"})
            continue
        final.append(seg)
    return final, rejected, stats


def run_one(key: str) -> dict:
    # 16k s16 才方便直接 wave+numpy 读；48k 母带是 s24，字节数对不上元素大小
    work = NORMALIZED / key / "source-vocals-16k.wav"
    if not work.exists():
        work = NORMALIZED / key / "source-16k.wav"
    wav = NORMALIZED / key / "source-vocals.wav"
    if not wav.exists():
        wav = NORMALIZED / key / "source.wav"
    vad = read_json(SLICES / key / "vad.json")
    words = read_json(ASR / f"{key}.words.json")["words"]
    frame = Db(frame_db(work))
    kept, rejected, stats = resolve(frame, vad["segments"], words)

    out = SLICES / key
    write_json(out / "segments.json", {"sourceKey": key, "wav": str(wav),
                                       "rules": RULES, "segments": kept})
    rows = ["index\tstart\tend\tduration\tkept\treject_reason\tflag"]
    for i, seg in enumerate(kept, start=1):
        rows.append(f"c{i:04d}\t{seg['start']}\t{seg['end']}\t"
                    f"{(seg['end'] - seg['start']) / 1000:.3f}\t1\t\t")
    for seg in sorted(rejected, key=lambda s: s["start"]):
        rows.append(f"-\t{seg['start']}\t{seg['end']}\t"
                    f"{(seg['end'] - seg['start']) / 1000:.3f}\t0\t{seg['reason']}\t")
    (out / "segments.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    durs = sorted((s["end"] - s["start"]) / 1000 for s in kept)

    def q(p: float) -> float:
        if not durs:
            return 0.0
        return round(durs[min(len(durs) - 1, int(p * (len(durs) - 1)))], 2)

    median = q(0.5)
    p25 = q(0.25)
    reason = "word-boundary-caps"  # 段偏短的根因：词帽把段裁到末词+60ms
    if median < RULES["medianFloorS"]:
        raise SystemExit(
            f"STOP：{key} 段长中位数 {median}s < {RULES['medianFloorS']}s（{reason}），"
            f"先调参数再往下跑（共 {len(durs)} 段）"
        )
    if p25 < RULES["p25FloorS"]:
        raise SystemExit(
            f"STOP：{key} 段长 P25 {p25}s < {RULES['p25FloorS']}s，碎片太多（{reason}），"
            f"共 {len(durs)} 段"
        )

    return {"key": key, "raw": len(vad["segments"]), "kept": len(kept),
            "rejected": len(rejected), "speech": round(sum(durs), 1),
            "min": round(min(durs), 2) if durs else 0,
            "max": round(max(durs), 2) if durs else 0,
            "median": median, "p25": p25, "p75": q(0.75),
            "floors": {"median": RULES["medianFloorS"], "p25": RULES["p25FloorS"]},
            "reason": reason,
            **stats}


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    summary = [run_one(k) for k in keys]
    write_json(SLICES / "rules-report.json", {"rules": RULES, "items": summary})
    for s in summary:
        print(f"[{s['key']}] vad {s['raw']} -> kept {s['kept']}（reject {s['rejected']}）  "
              f"{s['speech']}s  中位 {s['median']}s（{s['p25']}–{s['p75']}）  "
              f"词头 {s['headFromWord']} / 词尾 {s['tailFromWord']} / 谷退 {s['valleyFallback']}",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
