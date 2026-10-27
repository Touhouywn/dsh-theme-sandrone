"""02b slice-rules：vad 原始边界 -> 可切片的句表（裁剪规则的唯一实现处）。

只读 01-slices/<源键>/vad.json 和 00-normalized/<源键>/source-16k.wav，
产出 01-slices/<源键>/{segments.json, segments.tsv}。

为什么要有这一层：
fsmn-vad 对连续无停顿的段落按 60s 硬切（v1 里正好有 5 个 60.01s 的块），
块内部其实是一句一句、之间夹着数字静音（peak=0.000）。直接按 60s 块切，
或者只在最弱点断一次，都会切出纯静音的废片。所以 >10s 的块按内部停顿重新分解。

规则（v2-rules-2）：
- 帧 20ms / hop 10ms 算 RMS，dB = 20*log10(rms+1e-9)，>-38dB 判「有声」；
- ≤10s 的 vad 块原样保留（vad 自己的边界就是句界）；
- >10s 的块：按内部 ≥250ms 的停顿分解成有声段；分解后仍 >10s 的，
  在最弱的 250ms 窗口递归断开，找不到低于门限的窗口 → reject=too-long；
- 有声段裁到第一/最后一个有声帧（多出来的都是静音）；
- <0.6s：间隙 <250ms 并入相邻段（且合并后 ≤10s），否则 reject=too-short；
- 整块都没有声 → reject=no-active；
- 输出不重叠、按起点排序。
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import NORMALIZED, SLICES, SOURCE_KEYS, read_json, write_json  # noqa: E402

RULES = {
    "version": "v2-rules-3",
    "frameMs": 20,
    "hopMs": 10,
    "silenceDb": -38.0,
    "breakMs": 250,
    "forceBreakMs": 1200,
    "minDurS": 0.4,
    "fillerBelowS": 0.6,
    "maxDurS": 10.0,
    "splitWindowMs": 250,
    "headMs": 50,
    "tailMs": 80,
    "fadeInMs": 25,
    "fadeOutMs": 40,
}


def frame_db(wav_path: Path) -> "list[float]":
    """整轨逐帧 dB。帧长 20ms、hop 10ms。"""
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
    """按毫秒查帧 dB，省得把帧号换算散在各处。"""

    def __init__(self, db: list[float]):
        self.db = db
        self.hop = RULES["hopMs"]
        self.frame = RULES["frameMs"]
        self.thr = RULES["silenceDb"]

    def at(self, ms: float) -> float:
        i = int(ms // self.hop)
        return self.db[i] if 0 <= i < len(self.db) else -999.0

    def runs(self, start: int, end: int) -> list[list[int]]:
        """[start,end] 内的有声段：停顿 ≥breakMs 就断开。"""
        i0 = max(0, start // self.hop)
        i1 = min(len(self.db), end // self.hop + 1)
        pause_frames = max(1, RULES["breakMs"] // self.hop)
        runs: list[list[int]] = []
        begin = None
        idle = 0
        for i in range(i0, i1):
            if self.db[i] > self.thr:
                if begin is None:
                    begin = i
                idle = 0
            elif begin is not None:
                idle += 1
                if idle >= pause_frames:
                    runs.append([begin * self.hop, (i - idle + 1) * self.hop + self.frame])
                    begin = None
                    idle = 0
        if begin is not None:
            runs.append([begin * self.hop, min(end, (i1 - 1) * self.hop + self.frame)])
        return runs

    def weakest(self, start: int, end: int) -> int | None:
        """在内部找最弱的 250ms 窗口中心；窗口整体需低于门限。"""
        win = RULES["splitWindowMs"]
        min_piece = int(RULES["minDurS"] * 1000)
        lo, hi = start + min_piece, end - min_piece
        if hi - lo < win:
            return None
        best, best_db = None, 1e9
        for t in range(lo, hi - win + 1, self.hop):
            i0 = t // self.hop
            i1 = i0 + win // self.hop
            if i1 > len(self.db):
                break
            window = self.db[i0:i1]
            mean = sum(window) / len(window)
            if mean < best_db:
                best_db, best = mean, t
        if best is None or best_db > self.thr:
            return None
        return best + win // 2


def resolve(frame: Db, raw: list[dict]) -> tuple[list[dict], list[dict]]:
    min_ms = int(RULES["minDurS"] * 1000)
    max_ms = int(RULES["maxDurS"] * 1000)
    kept: list[dict] = []
    pieces: list[dict] = []
    rejected: list[dict] = []
    stats = {"decomposed": 0, "splitFallback": 0}

    for block in raw:
        start, end = block["start"], block["end"]
        if end - start <= max_ms:
            kept.append({"start": start, "end": end})
            continue

        stats["decomposed"] += 1
        runs = frame.runs(start, end)
        if not runs:
            rejected.append({"start": start, "end": end, "reason": "no-active"})
            continue
        # 先按内部停顿分解，再把相邻段并成「不超过 10s 的整句」：
        # 停顿 <250ms 是同句内换气，250ms–1.2s 也尽量并进去，
        # 只有 >1.2s 的沉默是硬断点（brief §02）。
        for lo, hi in runs:
            if pieces and hi - pieces[-1]["start"] <= max_ms and \
                    lo - pieces[-1]["end"] <= RULES["forceBreakMs"]:
                pieces[-1]["end"] = hi
            else:
                pieces.append({"start": lo, "end": hi})

        # 并完还超长（连续讲话），在最弱窗口断
        rebuilt: list[dict] = []
        for piece in pieces:
            stack = [piece]
            while stack:
                cur = stack.pop()
                if cur["end"] - cur["start"] <= max_ms:
                    rebuilt.append(cur)
                    continue
                point = frame.weakest(cur["start"], cur["end"])
                if point is None:
                    rejected.append({**cur, "reason": "too-long"})
                    stats["splitFallback"] += 1
                else:
                    stack.append({"start": point, "end": cur["end"]})
                    stack.append({"start": cur["start"], "end": point})
        pieces = rebuilt

    pieces = sorted(kept + pieces, key=lambda s: s["start"])

    # 碎片：只往 <250ms 的间隙里并，并完还要 ≤10s
    filler_ms = int(RULES["fillerBelowS"] * 1000)
    merged: list[dict] = []
    for seg in pieces:
        if merged and seg["end"] - seg["start"] < min_ms:
            prev = merged[-1]
            if seg["start"] - prev["end"] < RULES["breakMs"] and \
                    seg["end"] - prev["start"] <= max_ms:
                prev["end"] = seg["end"]
                continue
        if seg["end"] - seg["start"] < min_ms:
            rejected.append({**seg, "reason": "too-short"})
            continue
        if seg["end"] - seg["start"] > max_ms:
            rejected.append({**seg, "reason": "too-long"})
            continue
        dur = seg["end"] - seg["start"]
        merged.append({**seg, "flag": "filler" if dur < filler_ms else ""})

    # 去重叠（分解边界对齐帧，理论上不会叠，兜一手）
    final: list[dict] = []
    for seg in merged:
        if final and seg["start"] < final[-1]["end"]:
            seg = {"start": final[-1]["end"], "end": seg["end"], "flag": seg.get("flag", "")}
        if seg["end"] - seg["start"] < min_ms:
            rejected.append({**seg, "reason": "too-short-after-overlap"})
            continue
        final.append(seg)
    return final, rejected, stats


def run_one(key: str) -> dict:
    vad = read_json(SLICES / key / "vad.json")
    wav = NORMALIZED / key / "source-16k.wav"
    frame = Db(frame_db(wav))
    kept, rejected, stats = resolve(frame, vad["segments"])

    out = SLICES / key
    write_json(out / "segments.json", {
        "sourceKey": key, "wav": str(wav), "rules": RULES, "segments": kept,
    })

    rows = ["index\tstart\tend\tduration\tkept\treject_reason\tflag"]
    for idx, seg in enumerate(kept, start=1):
        rows.append(f"c{idx:04d}\t{seg['start']}\t{seg['end']}\t"
                    f"{(seg['end'] - seg['start']) / 1000:.3f}\t1\t\t{seg.get('flag', '')}")
    for seg in sorted(rejected, key=lambda s: s["start"]):
        rows.append(f"-\t{seg['start']}\t{seg['end']}\t"
                    f"{(seg['end'] - seg['start']) / 1000:.3f}\t0\t{seg['reason']}\t")
    (out / "segments.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    from collections import Counter

    durs = [(s["end"] - s["start"]) / 1000 for s in kept]
    return {
        "key": key,
        "raw": len(vad["segments"]),
        "kept": len(kept),
        "filler": sum(1 for s in kept if s.get("flag") == "filler"),
        "rejected": len(rejected),
        "reasons": dict(Counter(s["reason"] for s in rejected)),
        "speech": round(sum(durs), 1),
        "min": round(min(durs), 2) if durs else 0,
        "max": round(max(durs), 2) if durs else 0,
        "mean": round(sum(durs) / len(durs), 2) if durs else 0,
        **stats,
    }


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    summary = [run_one(k) for k in keys]
    write_json(SLICES / "rules-report.json", {"rules": RULES, "items": summary})
    for s in summary:
        print(f"[{s['key']}] raw {s['raw']} -> kept {s['kept']}（filler {s['filler']}）"
              f"  reject {s['reasons']}  speech={s['speech']}s  "
              f"{s['min']}–{s['max']}s mean {s['mean']}  分解 {s['decomposed']} 块")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
