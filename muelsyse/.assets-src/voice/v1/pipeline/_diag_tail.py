"""诊断：v2 的段为什么变短——是 whisper 词尾太早，还是能量尾巴真的长。

读 01-slices/<key>/segments.json（含 energyStart/energyEnd）与 02-asr/<key>.words.json。
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wordcut  # noqa: E402
from common import ASR, SLICES, read_json  # noqa: E402


def main(argv: list[str]) -> int:
    for key in argv:
        segs = read_json(SLICES / key / "segments.json")["segments"]
        words = read_json(ASR / f"{key}.words.json")["words"]
        tail_gaps, head_gaps, no_word = [], [], 0
        for s in segs:
            es, ee = s.get("energyStart"), s.get("energyEnd")
            if es is None or ee is None:
                continue
            lw = wordcut.last_word_end(words, es, ee)
            fw = wordcut.first_word_start(words, es, ee)
            if lw is None or fw is None:
                no_word += 1
                continue
            tail_gaps.append(ee - lw)
            head_gaps.append(fw - es)
        durs = [(s["end"] - s["start"]) / 1000 for s in segs]
        print(f"[{key}] 段 {len(segs)}  中位 {statistics.median(durs):.2f}s  总 {sum(durs):.1f}s")
        if tail_gaps:
            print(f"  energy_end - last_word.end  中位 {statistics.median(tail_gaps):.0f}ms  "
                  f"p90 {sorted(tail_gaps)[int(len(tail_gaps)*0.9)]:.0f}ms")
        if head_gaps:
            print(f"  first_word.start - energy_start 中位 {statistics.median(head_gaps):.0f}ms  "
                  f"p90 {sorted(head_gaps)[int(len(head_gaps)*0.9)]:.0f}ms")
        print(f"  找不到词的段: {no_word}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
