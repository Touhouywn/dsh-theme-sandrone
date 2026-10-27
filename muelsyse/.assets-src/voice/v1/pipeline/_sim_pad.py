"""模拟：把词边界垫大一点，段长中位会回到多少（不重切，只算）。"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wordcut  # noqa: E402
from common import ASR, SLICES, read_json  # noqa: E402

VARIANT = [
    ("现行 40/60", 50, 40, 40, 60),
    ("垫大 90/120", 50, 40, 90, 120),
    ("垫大 120/150", 50, 40, 120, 150),
    ("只靠能量", 50, 40, 0, 0),
]


def main(key: str) -> int:
    segs = read_json(SLICES / key / "segments.json")["segments"]
    words = read_json(ASR / f"{key}.words.json")["words"]
    for label, head_pad, tail_pad, w_h, w_t in VARIANT:
        durs = []
        for s in segs:
            es, ee = s.get("energyStart"), s.get("energyEnd")
            if es is None or ee is None:
                continue
            if w_h == 0:
                start, end = es - head_pad, ee + tail_pad
            else:
                lw = wordcut.last_word_end(words, es, ee)
                fw = wordcut.first_word_start(words, es, ee)
                start = es - head_pad if fw is None else max(es - head_pad, fw - w_h)
                end = ee + tail_pad if lw is None else min(ee + tail_pad, lw + w_t)
            if end - start >= 400:
                durs.append((end - start) / 1000)
        if durs:
            print(f"[{key}] {label:<14} n={len(durs):>4} 中位 {statistics.median(durs):.2f}s "
                  f"p25 {sorted(durs)[len(durs)//4]:.2f} 总 {sum(durs):.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "v2-story62"))
