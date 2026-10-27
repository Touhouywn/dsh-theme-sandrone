"""汇总：segments 统计 / tailOverrun 清单 / floor-drop / farewell 覆盖。只读不写。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2")

rules = json.loads((ROOT / "01-slices" / "rules-report.json").read_text(encoding="utf-8"))
print("== segments ==")
for s in rules["items"]:
    print(f"  {s['key']:<14} kept {s['kept']:>4}  中位 {s['median']}s  "
          f"p25 {s['p25']}  p75 {s['p75']}  语音 {s['speech']}s")

audit = json.loads((ROOT / "04-audit" / "audit.json").read_text(encoding="utf-8"))
t = audit["tailOverrun"]
print(f"\n== tailOverrun: {t['count']} 段（无词 {t['noWords']}）==")
for x in t["list"]:
    print(f"  {x['id']}  {x['overrunMs']:>7}ms  {x['sourceKey']}  {x['text']}")

print("\n== 高频意图 ==")
for name in ["affirm", "deny", "followup", "thanks", "greeting", "farewell", "error"]:
    c = audit["coverage"][name]
    print(f"  {name:<10} {c['count']:>3}/{c['need']}  bands={c['bands']}  ok={c['ok']}")

fd = json.loads((ROOT / "01-separate" / "floor-drop.json").read_text(encoding="utf-8"))
print("\n== floor-drop ==")
for k, v in fd["items"].items():
    print(f"  {k:<14} {v}")
