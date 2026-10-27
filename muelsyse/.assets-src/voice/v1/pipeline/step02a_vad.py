"""02a vad：16k 工作轨 -> 句级边界（voicekit vad 原样产物）。

只读 00-normalized/<源键>/source-16k.wav，产出 01-slices/<源键>/vad.json。
本步不做任何筛选：规则在 02b 落地，边界本身留原样，便于回看。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import LOGS, NORMALIZED, SLICES, SOURCE_KEYS, read_json, voicekit, write_json  # noqa: E402


def run_one(key: str) -> dict:
    work = NORMALIZED / key / "source-16k.wav"
    if not work.exists():
        raise SystemExit(f"[{key}] 缺 16k 工作轨：{work}")
    out = SLICES / key / "vad.json"
    log = LOGS / key / "02a-vad.log"
    code = voicekit(["vad", str(work), str(out)], log)
    if code != 0:
        raise SystemExit(f"[{key}] voicekit vad 失败，见 {log}")
    data = read_json(out)
    segs = data["segments"]
    speech = sum(s["end"] - s["start"] for s in segs) / 1000
    return {
        "sourceKey": key,
        "vadFile": str(out),
        "segments": len(segs),
        "speechSeconds": round(speech, 1),
        "firstMs": segs[0]["start"] if segs else None,
        "lastMs": segs[-1]["end"] if segs else None,
        "log": str(log),
    }


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    summary = [run_one(k) for k in keys]
    write_json(SLICES / "vad-summary.json", {"items": summary})
    for s in summary:
        print(f"[{s['sourceKey']}] {s['segments']} segments  speech={s['speechSeconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
