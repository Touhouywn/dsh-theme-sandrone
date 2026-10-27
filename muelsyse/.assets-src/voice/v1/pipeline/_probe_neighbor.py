"""看「见了」这一段的邻居：是不是前一段的尾巴把它的头压掉了。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2")
segs = json.loads((ROOT / "01-slices" / "v2-story62" / "segments.json").read_text(encoding="utf-8"))["segments"]
words = json.loads((ROOT / "02-asr" / "v2-story62.words.json").read_text(encoding="utf-8"))["words"]

target = None
for i, s in enumerate(segs):
    if s["start"] <= 2116880 <= s["end"]:
        target = i
        break
if target is None:
    print("没找到")
    raise SystemExit()

for i in range(max(0, target - 1), min(len(segs), target + 2)):
    s = segs[i]
    print(f"[{i}] clip {s['start']}–{s['end']}  energy {s.get('energyStart')}–{s.get('energyEnd')}")

s = segs[target]
near = [w for w in words
        if w["end"] * 1000 > s["start"] - 600 and w["start"] * 1000 < s["end"] + 600]
print("附近词:", [(round(w["start"], 2), round(w["end"], 2), w["word"]) for w in near])
