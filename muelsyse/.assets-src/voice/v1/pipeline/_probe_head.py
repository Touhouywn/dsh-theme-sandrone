"""按文本找段，打印 clip/energy/词起点，看头是不是被词帽夹掉了。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2")
cat = json.loads((ROOT / "stage" / "catalog.json").read_text(encoding="utf-8"))["clips"]

TARGETS = ["见了", "想再见一面", "桑多尼"]
for target in TARGETS:
    hits = [c for c in cat if c["text"] == target]
    for c in hits[:2]:
        fp = c["sourceFingerprint"]
        key = fp["sourceKey"]
        words = json.loads((ROOT / "02-asr" / f"{key}.words.json").read_text(encoding="utf-8"))["words"]
        es, ee = fp.get("energyStartMs"), fp.get("energyEndMs")
        near = [w for w in words if w["end"] * 1000 > es - 400 and w["start"] * 1000 < ee + 400]
        print(f"{c['id']} 「{c['text']}」 clip {fp['startMs']}–{fp['endMs']}  energy {es}–{ee}")
        print("   词:", [(round(w["start"], 2), round(w["end"], 2), w["word"]) for w in near[:6]])
