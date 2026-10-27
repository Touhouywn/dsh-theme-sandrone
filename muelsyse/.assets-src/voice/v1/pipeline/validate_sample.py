"""规则试切：抽一小批句子走 cut + asr，验证边界和转写链路。

只读 01-slices/<源键>/segments.json 与 00-normalized/<源键>/source-16k.wav；
产出 01-slices/_validate/{segments.json, clips/, asr.json}。
转写一次传整个目录（一个进程），不逐段开进程。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import LOGS, NORMALIZED, SLICES, read_json, voicekit, write_json  # noqa: E402
from step03_cut import cut_one  # noqa: E402

KEY = "v1-training"
OUT = SLICES / "_validate"
STRIDE = 12      # 按序号等距抽
SHORT = 8        # 再把最短的 8 段带上（碎片最容易出问题）
LIMIT = 32


def pick(segs: list[dict]) -> list[dict]:
    chosen = segs[::STRIDE][: LIMIT - SHORT]
    shorts = sorted(segs, key=lambda s: s["end"] - s["start"])[:SHORT]
    seen = {(s["start"], s["end"]) for s in chosen}
    for seg in shorts:
        if (seg["start"], seg["end"]) not in seen:
            chosen.append(seg)
            seen.add((seg["start"], seg["end"]))
    return chosen[:LIMIT]


def main() -> int:
    segs = read_json(SLICES / KEY / "segments.json")["segments"]
    chosen = pick(segs)
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "segments.json", {"sourceKey": KEY, "segments": chosen})

    wav = NORMALIZED / KEY / "source-16k.wav"
    clips = OUT / "clips"
    index, silent = cut_one(wav, chosen, clips, LOGS / KEY / "02c-validate-cut.log")
    write_json(clips / "index.json", {"sourceKey": KEY, "clips": index})

    code = voicekit(["asr", str(clips), str(OUT / "asr.json")], LOGS / KEY / "02c-validate-asr.log")
    if code != 0:
        raise SystemExit("voicekit asr 失败，见 logs")

    rows = read_json(OUT / "asr.json")["items"]
    print(f"clips {len(index)}  asr {len(rows)}  静音坏片 {len(silent)}")
    for c, row in zip(index, rows):
        print(f"  {c['id']} {c['duration']:>5.2f}s peak {c['peakDb']:>6.1f}dB  {row['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
