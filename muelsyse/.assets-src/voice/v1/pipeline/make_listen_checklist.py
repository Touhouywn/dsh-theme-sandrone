"""生成抽听清单：27 键模板段 + 每意图 top3 + 随机 5% + greeting/farewell/identity 全量。

只读 publish/catalog.json 与 publish/templates.json，产出 04-audit/listen-checklist.md。
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, read_json  # noqa: E402
from intents import INTENT_TAGS, TEMPLATE_KEYS  # noqa: E402

PUBLISH = ROOT / "publish"
AUDIT = ROOT / "04-audit"
RANDOM_PCT = 0.05
SEED = 20261027


def main() -> int:
    catalog = read_json(PUBLISH / "catalog.json")["clips"]
    templates = read_json(PUBLISH / "templates.json")["templates"]
    by_id = {c["id"]: c for c in catalog}
    usable = [c for c in catalog if c["usable"]]

    def line(cid: str) -> str:
        c = by_id[cid]
        return f"| `{cid}` | {c['text'][:30]} | {c['duration']:.2f}s | {c['asrScore']:.3f} |"

    out = ["# v2 抽听清单", "",
           f"库：{len(catalog)} 行 / {len(usable)} usable；模板 {len(templates)} 键。",
           "标 id / text / 时长；听的时候按「整句是否完整、有没有切到字」判，不按文本准不准判。", ""]

    out += ["## 一、27 键的模板段（每键必听）", ""]
    for key in TEMPLATE_KEYS:
        ids = templates.get(key, [])
        out.append(f"### {key}")
        if not ids:
            out += ["（空——L1 不走模板，落 L2 检索）", ""]
            continue
        out += ["| id | text | 时长 | asrScore |", "| --- | --- | ---: | ---: |"]
        out += [line(cid) for cid in ids]
        out.append("")

    out += ["## 二、每意图 top3（按 asrScore 降序）", ""]
    for intent, tags in INTENT_TAGS.items():
        pool = [c for t in tags for c in usable if t in c["tags"]]
        ranked = sorted({c["id"]: c for c in pool}.values(),
                        key=lambda c: (-c["asrScore"], c["duration"], c["id"]))[:3]
        if not ranked:
            continue
        out += [f"### {intent}", "| id | text | 时长 | asrScore |",
                "| --- | --- | ---: | ---: |"]
        out += [line(c["id"]) for c in ranked]
        out.append("")

    rng = random.Random(SEED)
    picked = rng.sample(usable, max(1, int(len(catalog) * RANDOM_PCT)))
    out += [f"## 三、随机 {RANDOM_PCT:.0%}（{len(picked)} 段）", "",
            "| id | text | 时长 | asrScore |", "| --- | --- | ---: | ---: |"]
    out += [line(c["id"]) for c in sorted(picked, key=lambda c: c["id"])]

    full = [c for c in catalog if set(c["tags"]) & {"greeting", "farewell", "identity"}]
    out += ["", f"## 四、greeting / farewell / identity 全量（{len(full)} 段）", "",
            "| id | text | 时长 | asrScore |", "| --- | --- | ---: | ---: |"]
    out += [line(c["id"]) for c in sorted(full, key=lambda c: c["id"])]

    AUDIT.mkdir(parents=True, exist_ok=True)
    (AUDIT / "listen-checklist.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"写了 {AUDIT / 'listen-checklist.md'}")
    print(f"模板段 {len([k for k in TEMPLATE_KEYS if templates.get(k)])} 键 / "
          f"随机 {len(picked)} 段 / 全量 {len(full)} 段")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
