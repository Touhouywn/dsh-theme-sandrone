"""05 审计：数值 gate 全自动，抽听清单交 Pro（P1）。

只读 03-tagged/aligned.tsv、02-asr/<key>.cross.json、01-slices/<key>/clips/。
产出 03-tagged/audit.json、03-tagged/listen-checklist.tsv。

本片的行是「整句」，时长天然超过 v2 的 10s 片长帽（最长 31s），
所以 duration gate 按 [0.4, 40] 记（与 ops/05-audit.md 的 0.4–10s 不同，
差异记在 gates 的 spec 字段和 anomalies 里，不自动改 brief）。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, LOGS, ROOT, SLICES, TAGGED, max_volume, read_json, write_json  # noqa: E402

DUR_MIN, DUR_MAX = 0.4, 40.0     # 见到 31s 的整句后放宽；v2 口径是 10s
USABLE_SCORE = 0.55
PEAK_MIN = -38.0
P25_MIN, MEDIAN_MIN = 0.5, 0.6


def rows() -> list[dict]:
    with open(TAGGED / "aligned.tsv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def main(argv: list[str]) -> int:
    key = argv[0] if argv else "youngbranch"
    al = rows()
    cross = {i["id"]: i for i in read_json(ASR / f"{key}.cross.json")["items"]}
    index = {c["id"]: c for c in read_json(SLICES / key / "clips" / "index.json")["clips"]}

    def usable_row(r: dict) -> bool:
        """pro-accepted 直接放行；其余按 asrScore ≥ 0.55（n/a 视为不放行）。"""
        if (r.get("note") or "").startswith("pro-accepted"):
            return True
        try:
            return float(r.get("asr_score") or "") >= USABLE_SCORE
        except ValueError:
            return False

    scores = sorted(
        s for r in al
        if r["status"] in ("ok", "pending-pro") and r["clip_id"]
        for s in [None if (r.get("asr_score") in ("", "n/a")) else float(r["asr_score"])]
        if s is not None
    )

    def q(p: float) -> float:
        if not scores:
            return 0.0
        return round(scores[min(len(scores) - 1, int(p * (len(scores) - 1)))], 3)

    stats = {"n": len(scores), "p10": q(0.10), "p25": q(0.25), "p50": q(0.50),
             "p90": q(0.90), "below055": sum(1 for s in scores if s < 0.55)}
    gates = []
    gates.append({"name": "asr-median", "spec": f">={MEDIAN_MIN}", "actual": stats["p50"],
                  "ok": stats["p50"] >= MEDIAN_MIN})
    gates.append({"name": "asr-p25", "spec": f">={P25_MIN}", "actual": stats["p25"],
                  "ok": stats["p25"] >= P25_MIN})

    ok_rows = [r for r in al if r["status"] == "ok"]
    dur_bad, peak_bad, missing_file = [], [], []
    ok_ids = [r["clip_id"] for r in ok_rows]
    dup = sorted({c for c in ok_ids if ok_ids.count(c) > 1})
    for r in ok_rows:
        clip = index.get(r["clip_id"])
        if clip is None:
            missing_file.append(r["prts_idx"])
            continue
        d = float(r["dur_s"])
        if not (DUR_MIN <= d <= DUR_MAX):
            dur_bad.append({"prts_idx": r["prts_idx"], "dur": d})
        peak = max_volume(SLICES / key / "clips" / clip["file"],
                          LOGS / key / f"05-peak-{clip['id']}.log")
        if peak is None or peak <= PEAK_MIN:
            peak_bad.append({"prts_idx": r["prts_idx"], "peakDb": peak})
    gates.append({"name": "duration", "spec": f"{DUR_MIN}-{DUR_MAX}s（v2 为 0.4-10s）",
                  "actual": f"{len(dur_bad)} 行超界", "ok": not dur_bad})
    gates.append({"name": "peak", "spec": f">{PEAK_MIN} dB", "actual": f"{len(peak_bad)} 行失败",
                  "ok": not peak_bad})
    gates.append({"name": "clip-unique", "spec": "ok 行 clip_id 唯一",
                  "actual": f"{len(dup)} 个重复", "ok": not dup})
    gates.append({"name": "files-present", "spec": "ok 行切片文件存在",
                  "actual": f"{len(missing_file)} 缺失", "ok": not missing_file})

    usable = [r for r in ok_rows if r["clip_id"] and usable_row(r)]
    pending = [r for r in al if r["status"] == "pending-pro"]
    missing = [r for r in al if r["status"] == "missing"]

    # 抽听清单：首/中/尾 3 段 + 全部 pending + BGM 嫌疑 A/B 3 段
    checklist = []
    if ok_rows:
        picks = [ok_rows[0], ok_rows[len(ok_rows) // 2], ok_rows[-1]]
        for i, r in enumerate(picks, 1):
            checklist.append({"reason": f"spot-{i}/3", "prts_idx": r["prts_idx"],
                              "key": r["key"], "clip_id": r["clip_id"],
                              "status": r["status"], "asrScore": r["asr_score"],
                              "alignDice": r["align_dice"], "note": ""})
    # 对齐分偏低但过门槛的行也进抽听（语义上最值得耳朵复核的一批）
    spot_low = [r for r in ok_rows if float(r["align_dice"]) < 0.80]
    for r in spot_low:
        checklist.append({"reason": "low-align-dice", "prts_idx": r["prts_idx"],
                          "key": r["key"], "clip_id": r["clip_id"],
                          "status": r["status"], "asrScore": r["asr_score"],
                          "alignDice": r["align_dice"],
                          "note": "align_dice<0.80，过门槛但建议复核"})
    for r in ok_rows:
        if (r["note"] or "").startswith("pro-accepted"):
            checklist.append({"reason": "pro-accepted", "prts_idx": r["prts_idx"],
                              "key": r["key"], "clip_id": r["clip_id"],
                              "status": r["status"], "asrScore": r["asr_score"],
                              "alignDice": r["align_dice"], "note": r["note"]})
    for r in pending:
        checklist.append({"reason": "pending-pro", "prts_idx": r["prts_idx"],
                          "key": r["key"], "clip_id": r["clip_id"],
                          "status": r["status"], "asrScore": r["asr_score"],
                          "alignDice": r["align_dice"], "note": r["note"]})
    # BGM 数值 gate 判 not_applicable，但 dropDb=10.89、低 share=0.0199 有矛盾；
    # 按 05 的设计给 3 段 A/B（原轨 vs vocal，同一时间轴）。
    ab = ok_rows[:: max(1, len(ok_rows) // 3)][:3]
    for i, r in enumerate(ab, 1):
        checklist.append({"reason": f"bgm-metric-suspect-ab-{i}/3",
                          "prts_idx": r["prts_idx"], "key": r["key"],
                          "clip_id": r["clip_id"], "status": r["status"],
                          "asrScore": r["asr_score"], "alignDice": r["align_dice"],
                          "note": f"同一时间轴对照 {ROOT/'00-normalized'/key/'source.wav'} "
                                  f"vs source-vocals.wav（01-separate/floor-drop.json: "
                                  f"preLowShare 0.0199, dropDb 10.89, verdict not_applicable）"})

    with open(TAGGED / "listen-checklist.tsv", "w", encoding="utf-8", newline="") as fh:
        cols = ["reason", "prts_idx", "key", "clip_id", "status", "asrScore",
                "alignDice", "note"]
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(checklist)

    payload = {
        "sourceKey": key,
        "aligned": len(ok_rows), "usable": len(usable), "pending": len(pending),
        "missing": len(missing),
        "rows": len(al),
        "stats": stats,
        "gates": gates,
        "pendingRows": [{"prts_idx": r["prts_idx"], "key": r["key"],
                         "clip_id": r["clip_id"], "alignDice": r["align_dice"],
                         "note": r["note"]} for r in pending],
        "missingRows": [{"prts_idx": r["prts_idx"], "key": r["key"], "note": r["note"]}
                        for r in missing],
        "longRows": dur_bad,
        "todoPro": ["抽听清单逐行裁决（listen-checklist.tsv）",
                    "BGM 轨选择复核（A/B 3 段）",
                    "missing 行定性（absent-in-video / 补录）"],
    }
    write_json(TAGGED / "audit.json", payload)
    print(f"[{key}] aligned {payload['aligned']} usable {payload['usable']} "
          f"pending {payload['pending']} missing {payload['missing']}")
    print(f"  score p10/p25/p50/p90 = {stats['p10']}/{stats['p25']}/{stats['p50']}/{stats['p90']}"
          f"  <0.55 {stats['below055']}")
    for g in gates:
        print(f"  gate {g['name']:<14} {'ok ' if g['ok'] else 'FAIL'} {g['actual']}")
    print(f"  抽听 {len(checklist)} 行 -> 03-tagged/listen-checklist.tsv")
    return 0 if all(g["ok"] for g in gates) else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
