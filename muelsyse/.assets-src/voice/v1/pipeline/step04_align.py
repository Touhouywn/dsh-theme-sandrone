"""04 align：把切片按时间序对齐到 skeleton-38.tsv（38 行官方日文文本）。

只读：
  skeleton-38.tsv
  02-asr/<key>.json           SenseVoice（textClean 已含假名）
  02-asr/<key>.cross.json     whisper 互校（asrScore / whisperRaw）
  01-slices/<key>/clips/index.json

产出：03-tagged/aligned.tsv
  骨架 6 列 + clip_id,source_start_ms,source_end_ms,dur_s,sense_ja,whisper_ja,
  asr_score,align_dice,status,note

算法（顺序 DP，贪心语义）：
  s(i,j) = max(Dice(官方行, sense_j), Dice(官方行, whisper_j))，均先过 norm_ja。
  dp[i][j] = max(跳行 dp[i-1][j], 跳片 dp[i][j-1],
                 匹配 dp[i-1][j-1] + s(i,j)  [仅 s ≥ MATCH_MIN])
  s ≥ 行门槛（≤12 字 0.45 / 长 0.42）→ ok；否则 pending-pro（附 top-2 候选）。
  未被 DP 选中的行：候选来自「前后已匹配切片之间、尚未被用掉」的切片；
  有候选且最佳 ≥ PENDING_MIN → pending-pro，否则 missing。

运行：python step04_align.py [源键]
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, ROOT, SLICES, TAGGED, read_json  # noqa: E402
from norm_ja import dice, norm, threshold  # noqa: E402

SKELETON = ROOT / "skeleton-38.tsv"
OUT = TAGGED / "aligned.tsv"
EXPECTED_ROWS = 38
ALIGN_GATE = 0.85
MATCH_MIN = 0.20   # DP 允许配对的最低分（低于此视为无关系）
PENDING_MIN = 0.00  # 未配上的行，只要区间里有未用切片就给候选（pending），空区间才 missing
TAG_RE = re.compile(r"<\|[^|]*\|>")


def load_skeleton() -> list[dict]:
    with open(SKELETON, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"STOP：骨架行数 {len(rows)} != {EXPECTED_ROWS}，不写结果")
    return rows


def load_clips(key: str) -> list[dict]:
    index = read_json(SLICES / key / "clips" / "index.json")["clips"]
    return sorted(index, key=lambda c: c["sourceStart"])


def load_texts(key: str) -> tuple[dict, dict]:
    asr = {i["id"]: i for i in read_json(ASR / f"{key}.json")["items"]}
    cross = {i["id"]: i for i in read_json(ASR / f"{key}.cross.json")["items"]}
    return asr, cross


def score_row(row_norm: str, clip_id: str, asr: dict, cross: dict) -> tuple[float, str, str]:
    item = asr.get(clip_id, {})
    sense_raw = item.get("textClean") or TAG_RE.sub("", item.get("raw") or "")
    sense = norm(sense_raw)
    whisper = norm((cross.get(clip_id) or {}).get("whisperRaw") or "")
    s = max(dice(row_norm, sense), dice(row_norm, whisper))
    return s, sense, whisper


def align(key: str) -> dict:
    rows = load_skeleton()
    clips = load_clips(key)
    asr, cross = load_texts(key)
    n, m = len(rows), len(clips)
    if m == 0:
        raise SystemExit("STOP：没有切片")

    row_norm = [norm(r["ja_text"]) for r in rows]
    scores = [[0.0] * m for _ in range(n)]
    sense_txt = [[""] * m for _ in range(n)]
    whisper_txt = [[""] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s, sense, whisper = score_row(row_norm[i], clips[j]["id"], asr, cross)
            scores[i][j], sense_txt[i][j], whisper_txt[i][j] = s, sense, whisper

    # ---- 顺序 DP ----
    NEG = -1e9
    dp = [[NEG] * (m + 1) for _ in range(n + 1)]
    pick = [[0] * (m + 1) for _ in range(n + 1)]  # 0 跳行 1 跳片 2 匹配
    for j in range(m + 1):
        dp[0][j] = 0.0
        pick[0][j] = 1
    for i in range(1, n + 1):
        dp[i][0] = 0.0
        pick[i][0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best, how = dp[i - 1][j], 0          # 跳行
            if dp[i][j - 1] > best + 1e-12:      # 跳片
                best, how = dp[i][j - 1], 1
            s = scores[i - 1][j - 1]
            if s >= MATCH_MIN and dp[i - 1][j - 1] + s > best + 1e-12:
                best, how = dp[i - 1][j - 1] + s, 2
            dp[i][j], pick[i][j] = best, how

    matched: dict[int, int] = {}
    i, j = n, m
    while i > 0 and j > 0:
        how = pick[i][j]
        if how == 2:
            matched[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif how == 0:
            i -= 1
        else:
            j -= 1

    used = set(matched.values())
    # 每行的位置区间：前后已匹配切片之间
    order = sorted(matched)  # 行号升序 == 切片号升序
    # 未匹配行也要有前后已匹配切片位置：扫全部行，取最近的前/后匹配行
    prev_clip, next_clip = {}, {}
    last = -1
    for ri in range(n):
        prev_clip[ri] = last
        if ri in matched:
            last = matched[ri]
    last = m
    for ri in range(n - 1, -1, -1):
        next_clip[ri] = last
        if ri in matched:
            last = matched[ri]

    out_rows, pending, missing = [], [], []
    ok = 0
    for i, row in enumerate(rows):
        cid = sid = eid = dur = None
        sense = whisper = ""
        a_score = None
        s_best, threshold_i = 0.0, threshold(row_norm[i])
        note = ""
        if i in matched:
            j = matched[i]
            clip = clips[j]
            cid = clip["id"]
            sid, eid, dur = clip["sourceStart"], clip["sourceEnd"], clip["duration"]
            sense, whisper = sense_txt[i][j], whisper_txt[i][j]
            s_best = scores[i][j]
            a_score = (cross.get(cid) or {}).get("asrScore")
            if s_best >= threshold_i:
                status = "ok"
                ok += 1
            else:
                status = "pending-pro"
                cand = sorted(
                    ((scores[i][k], clips[k]["id"]) for k in range(m)
                     if k not in used and scores[i][k] >= MATCH_MIN
                     and prev_clip.get(i, -1) < k < next_clip.get(i, m)),
                    reverse=True,
                )[:2]
                note = "below-threshold; top2=" + "/".join(f"{c}({s:.3f})" for s, c in cand)
                pending.append((row, s_best, note))
        else:
            lo = prev_clip.get(i, -1)
            hi = next_clip.get(i, m)
            cand = sorted(
                ((scores[i][k], clips[k]["id"]) for k in range(lo + 1, hi)
                 if k not in used),
                reverse=True,
            )[:2]
            if cand and cand[0][0] >= PENDING_MIN:
                status = "pending-pro"
                cid = cand[0][1]
                note = "unmatched; top2=" + "/".join(f"{c}({s:.3f})" for s, c in cand)
                s_best = cand[0][0]
                pending.append((row, s_best, note))
            else:
                status = "missing"
                note = "absent-in-video" if hi <= lo + 1 else "no-candidate"
                missing.append((row, note))
        out_rows.append({
            **row,
            "clip_id": cid or "",
            "source_start_ms": sid if sid is not None else "",
            "source_end_ms": eid if eid is not None else "",
            "dur_s": dur if dur is not None else "",
            "sense_ja": sense,
            "whisper_ja": whisper,
            "asr_score": a_score if a_score is not None else "",
            "align_dice": round(s_best, 3),
            "status": status,
            "note": note,
        })

    # ---- 断言 ----
    ok_ids = [r["clip_id"] for r in out_rows if r["status"] == "ok"]
    dup = {c for c in ok_ids if ok_ids.count(c) > 1}
    if dup:
        raise SystemExit(f"STOP：ok 行 clip_id 重复 {sorted(dup)}")
    rate = ok / EXPECTED_ROWS

    # ---- 写盘 ----
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols = ["prts_idx", "key", "trigger", "cn_audio", "cn_text", "ja_text",
            "clip_id", "source_start_ms", "source_end_ms", "dur_s",
            "sense_ja", "whisper_ja", "asr_score", "align_dice", "status", "note"]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(out_rows)

    return {
        "key": key, "rows": n, "clips": m, "ok": ok, "pending": len(pending),
        "missing": len(missing), "alignedRate": round(rate, 3),
        "gate": {"name": "alignedRate", "expect": f">={ALIGN_GATE}", "actual": round(rate, 3),
                 "ok": rate >= ALIGN_GATE},
        "pendingRows": [{"prts_idx": r["prts_idx"], "key": r["key"],
                         "dice": round(s, 3), "note": note} for r, s, note in pending],
        "missingRows": [{"prts_idx": r["prts_idx"], "key": r["key"], "note": note}
                        for r, note in missing],
    }


def main(argv: list[str]) -> int:
    keys = argv or ["youngbranch"]
    bad = 0
    for key in keys:
        rep = align(key)
        print(f"[{key}] rows {rep['rows']}  clips {rep['clips']}  ok {rep['ok']}"
              f"  pending {rep['pending']}  missing {rep['missing']}"
              f"  alignedRate {rep['alignedRate']}")
        for r in rep["pendingRows"]:
            print(f"  PENDING {r['prts_idx']:>2} {r['key']}  {r['dice']}  {r['note']}")
        for r in rep["missingRows"]:
            print(f"  MISSING {r['prts_idx']:>2} {r['key']}  {r['note']}")
        if not rep["gate"]["ok"]:
            print(f"  STOP：alignedRate {rep['alignedRate']} < {ALIGN_GATE}")
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
