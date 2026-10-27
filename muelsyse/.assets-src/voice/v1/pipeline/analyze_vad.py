"""看 vad 原始边界的长相：时长分布、超长/超短计数、跨源对照。

只读 01-slices/<源键>/vad.json。不改任何边界，结论落 01-slices/vad-analysis.md。
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import SLICES, SOURCE_KEYS, read_json  # noqa: E402

BUCKETS = [(0, 0.6), (0.6, 1.5), (1.5, 3), (3, 6), (6, 10), (10, 20), (20, 1e9)]


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[idx]


def analyze(key: str) -> dict:
    data = read_json(SLICES / key / "vad.json")
    segs = data["segments"]
    durs = [(s["end"] - s["start"]) / 1000 for s in segs]
    gaps = [(segs[i + 1]["start"] - segs[i]["end"]) / 1000 for i in range(len(segs) - 1)]
    bucket = {}
    for lo, hi in BUCKETS:
        label = f"{lo:g}-{hi:g}" if hi < 1e9 else f">{lo:g}"
        bucket[label] = sum(1 for d in durs if lo <= d < hi)
    return {
        "key": key,
        "n": len(segs),
        "total": round(sum(durs), 1),
        "min": round(min(durs), 2) if durs else 0,
        "p10": round(pct(durs, 0.10), 2),
        "p50": round(pct(durs, 0.50), 2),
        "p90": round(pct(durs, 0.90), 2),
        "max": round(max(durs), 2) if durs else 0,
        "mean": round(statistics.mean(durs), 2) if durs else 0,
        "buckets": bucket,
        "tooShort": sum(1 for d in durs if d < 0.6),
        "tooLong": sum(1 for d in durs if d > 10),
        "gapP50": round(pct(gaps, 0.50), 2),
        "gapUnder250": sum(1 for g in gaps if g < 0.25),
        "gapOver1200": sum(1 for g in gaps if g > 1.2),
        "longestFirst": [
            {"start": s["start"], "end": s["end"], "dur": round((s["end"] - s["start"]) / 1000, 2)}
            for s in sorted(segs, key=lambda s: s["end"] - s["start"], reverse=True)[:5]
        ],
    }


def main() -> int:
    keys = list(SOURCE_KEYS)
    rows = [analyze(k) for k in keys]
    lines = ["# vad 原始边界体检（voicekit fsmn-vad）", ""]
    lines.append("| 源 | 段数 | 语音总长 | min | p10 | p50 | p90 | max | <0.6s | >10s |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in rows:
        lines.append(
            f"| {r['key']} | {r['n']} | {r['total']}s | {r['min']} | {r['p10']} | {r['p50']} | "
            f"{r['p90']} | {r['max']} | {r['tooShort']} | {r['tooLong']} |"
        )
    lines += ["", "## 时长档分布（秒；left-closed）", ""]
    head = "| 源 | " + " | ".join(
        (f"{lo:g}-{hi:g}" if hi < 1e9 else f">{lo:g}") for lo, hi in BUCKETS
    ) + " |"
    lines.append(head)
    lines.append("| --- | " + " | ".join("---:" for _ in BUCKETS) + " |")
    for r in rows:
        lines.append(f"| {r['key']} | " + " | ".join(str(v) for v in r["buckets"].values()) + " |")
    lines += ["", "## 间隙", "", "| 源 | p50 间隙 | <250ms | >1200ms |", "| --- | ---: | ---: | ---: |"]
    for r in rows:
        lines.append(f"| {r['key']} | {r['gapP50']}s | {r['gapUnder250']} | {r['gapOver1200']} |")
    lines += ["", "## 最长的五段", ""]
    for r in rows:
        lines.append(f"- **{r['key']}**：" + "，".join(
            f"{x['start']}–{x['end']}ms ({x['dur']}s)" for x in r["longestFirst"]
        ))
    (SLICES / "vad-analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
