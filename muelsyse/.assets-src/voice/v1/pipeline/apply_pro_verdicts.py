"""落地 Pro 裁决（03-tagged/PRO-VERDICT.md）：21 采纳、38 加回、43 维持 missing。

只改 aligned.tsv 的这三行（status/note/asr_score），不动其他行、不动音频。
05/06 按 note 前缀 `pro-accepted` 放行，不再被 asrScore 机械拦截。
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, SLICES, TAGGED, read_json, write_json  # noqa: E402

ALIGNED = TAGGED / "aligned.tsv"
OUT = TAGGED / "pro-verdicts-applied.json"

RULES = {
    "21": {"status": "ok", "asr_score": "n/a",
           "note": "pro-accepted-short-clip"},
    "38": {"status": "ok",
           "note": "pro-accepted-whisper-tail-hallucination"},
    "43": {"status": "missing", "note": "absent-in-video"},
}


def main(argv: list[str]) -> int:
    with open(ALIGNED, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        cols = reader.fieldnames
        rows = list(reader)

    # 行 21 在 DP 里是 unmatched，clip_id 是空的：裁决采纳后补上 c0021 与时间轴
    clips = {c["id"]: c for c in read_json(SLICES / "youngbranch" / "clips" / "index.json")["clips"]}
    asr = {i["id"]: i for i in read_json(ASR / "youngbranch.json")["items"]}
    cross = {i["id"]: i for i in read_json(ASR / "youngbranch.cross.json")["items"]}

    applied = []
    for r in rows:
        rule = RULES.get(r["prts_idx"])
        if not rule:
            continue
        before = (r["status"], r["note"])
        r["status"] = rule["status"]
        r["note"] = rule["note"]
        if "asr_score" in rule:
            r["asr_score"] = rule["asr_score"]
        if r["prts_idx"] == "21" and not r["dur_s"]:
            c = clips["c0021"]
            r["clip_id"] = "c0021"
            r["source_start_ms"] = str(c["sourceStart"])
            r["source_end_ms"] = str(c["sourceEnd"])
            r["dur_s"] = str(c["duration"])
            r["sense_ja"] = (asr.get("c0021") or {}).get("textClean", "")
            r["whisper_ja"] = (cross.get("c0021") or {}).get("whisperRaw", "")
            # align_dice 保持 04 的 0.0（官方文本 vs 两路子串碎片），不拿互校 dice 冒充
        applied.append({"prts_idx": r["prts_idx"], "key": r["key"],
                        "clip_id": r["clip_id"], "before": before,
                        "after": (r["status"], r["note"]),
                        "asr_score": r["asr_score"], "align_dice": r["align_dice"]})

    missing = [p for p in RULES if p not in {r["prts_idx"] for r in rows}]
    if missing:
        raise SystemExit(f"STOP：骨架里找不到要裁决的行 {missing}")

    with open(ALIGNED, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    write_json(OUT, {"verdicts": applied,
                     "statusCounts": {s: sum(1 for r in rows if r["status"] == s)
                                      for s in ("ok", "pending-pro", "missing")}})
    for a in applied:
        print(f"[{a['prts_idx']}] {a['before']} -> {a['after']}  "
              f"asr={a['asr_score']} dice={a['align_dice']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
