"""05 build：切片 + 打标 -> stage/ 里的 clip 与 catalog v2（不碰已发布库）。

只读：
  01-slices/<源键>/clips/{*.wav,index.json}
  00-normalized/<源键>/source.wav        （48k 母带，编码音源）
  00-normalized/<源键>/meta.json         （源 sha256）
  03-tagged/tags.tsv                     （标签 / asrScore / usable）
  旧库 catalog.json                      （id 沿用）

产出：
  stage/clips/<id>.ogg              48k mono opus 40k，淡入淡出 5/5 ms（与切片同规则）
  stage/catalog.json                catalog v2
  stage/templates.json              11 键，按 tags 选段（不再按旧 id 平移）
  stage/templates-unmapped.json     留空的键与原因

id 规则（修正稿 §1）：
  归一文本与旧 catalog 里「同一 id」的 text 完全相等，且该 id 本轮未占用 → 沿用旧 id；
  否则发新号，从当前最大号 +1 续（c0481 起）。
  断言：id 全局唯一；每条记录保留 sourceKey。
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    FFMPEG,
    NORMALIZED,
    ROOT,
    SLICES,
    SOURCE_KEYS,
    TAGGED,
    _run_to_log,
    read_json,
    write_json,
)
from intents import (  # noqa: E402
    COMFORT_WORDS,
    TEMPLATE_KEYS,
    TEMPLATE_TAG,
    is_error_shared,
    load_pins,
)

OLD = ROOT / "baseline"   # 冻结的 480 段旧库基线（发布后 assets 已被覆盖，不能当基线）
STAGE = ROOT / "stage"
LOGS = ROOT / "logs" / "_build"

HEAD_MS = 0          # v4 的边界已经是最终值（词边界 + 能量谷），不再二次留白
TAIL_MS = 0
FADE_MS = 25         # 淡入
FADE_OUT_MS = 40     # 淡出
STEM = "vocals"      # 人声分离轨；要 A/B 回原轨时改 "original"
SOURCE_WAV = "source-vocals.wav"
BITRATE = "40k"


def norm(text: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", unicodedata.normalize("NFKC", text or "")))


def read_tags() -> list[dict]:
    lines = (TAGGED / "tags.tsv").read_text(encoding="utf-8").splitlines()
    head = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        if not line:
            continue
        cells = line.split("\t")
        rec = dict(zip(head, cells))
        rec["duration"] = float(rec["duration"])
        rec["asrScore"] = float(rec["asrScore"])
        rec["usable"] = rec["usable"] == "1"
        rec["filler"] = rec["filler"] == "1"
        rec["nameHit"] = rec["nameHit"] == "1"
        rec["tags"] = [t for t in rec["tags"].split(",") if t]
        rec["text"] = cells[-1]
        rows.append(rec)
    return rows


def allocate(rows: list[dict], old: dict, next_id: int,
             pins: dict) -> tuple[list[tuple[dict, str]], int]:
    """返回 [(row, id)] 与下一个可用号。

    先给 pinned 段钉位（它们必须拿回原 id），再处理其余段：
    文本与基线旧 id 完全相等则沿用，否则发新号。
    分两趟是为了防止「新号先撞上后面才处理到的 pinned id」。
    """
    forced = pins.get("by_slice", {})
    by_key = {(r["sourceKey"], r["id"]): r for r in rows}
    old_by_id = {c["id"]: c for c in old["clips"]}
    used: set[str] = set()
    out: list[tuple[dict, str]] = []
    pinned_rows: set[int] = set()

    for key, cid in forced.items():
        row = by_key.get(key)
        if row is None or cid in used:
            continue
        used.add(cid)
        out.append((row, cid))
        pinned_rows.add(id(row))

    for row in rows:
        if id(row) in pinned_rows:
            continue
        key = norm(row["text"])
        picked = None
        for old_id, old_clip in old_by_id.items():
            if old_id in used or not key:
                continue
            if norm(old_clip["text"]) == key:
                picked = old_id
                break
        if picked is None:
            while f"c{next_id:04d}" in used or f"c{next_id:04d}" in old_by_id:
                next_id += 1
            picked = f"c{next_id:04d}"
            next_id += 1
        used.add(picked)
        out.append((row, picked))
    return out, next_id


def pick(entries: list[dict], pred, limit: int = 1) -> list[dict]:
    """该标签内 usable 的段：asrScore 降序、时长升序取第一条；<0.6 不入选。"""
    pool = [e for e in entries if e["usable"] and e["asrScore"] >= 0.6 and pred(e)]
    pool.sort(key=lambda e: (-e["asrScore"], e["duration"], e["id"]))
    return pool[:limit]


def build_templates(entries: list[dict]) -> tuple[dict, dict]:
    """P1.3：27 键 = 旧 11 键 ∪ 新 21 表。

    通用规则：该 tag 内 usable 的段按（asrScore 降序、时长升序）取第一条，
    asrScore < 0.6 不入选；选不出就留空并记入 missing-intents。
    code / fact 本来就该空（L4 与 L3 已覆盖）。
    error 从 §3 literal 集合里选；comfort 走文本直选、不靠 tagger；
    soft 与 comfort 同一 id；enable 两段 = [ack/affirm 最短段, traveler 段]；
    goodnight 与 sleep 共用 sleep 标签那一段。
    """
    by_tag = {tag: [e for e in entries if tag in e["tags"] and e["usable"]] for tag in
              {t for t in TEMPLATE_TAG.values() if t}}

    templates: dict[str, list[str]] = {}
    gaps: dict[str, dict] = {}

    for key in TEMPLATE_KEYS:
        if key in ("code", "fact"):
            templates[key] = []
            continue
        if key == "soft":
            continue  # 下面统一按 comfort 复制
        if key == "enable":
            first = [e for e in entries if e["usable"] and e["asrScore"] >= 0.6
                     and set(e["tags"]) & {"ack", "affirm"}]
            first.sort(key=lambda e: (e["duration"], -e["asrScore"], e["id"]))
            second = [e for e in entries if e["usable"] and e["asrScore"] >= 0.6
                      and "traveler" in e["tags"] and e["duration"] <= 5]
            second.sort(key=lambda e: (-e["asrScore"], e["duration"], e["id"]))
            ids = [e["id"] for e in (first[:1] + second[:1])]
            templates[key] = list(dict.fromkeys(ids))
            if len(templates[key]) < 2:
                gaps[key] = {"reason": "enable 两段凑不齐", "ids": templates[key]}
            continue
        if key == "comfort":
            pool = [e for e in entries if e["usable"] and e["asrScore"] >= 0.6
                    and COMFORT_WORDS.search(str(e.get("text", "")) + " " + str(e.get("asrText", "")))]
            pool.sort(key=lambda e: (-e["asrScore"], e["duration"], e["id"]))
            chosen = pool[:1]
        elif key == "error":
            chosen = pick(entries, lambda e: is_error_shared(e))
        else:
            tag = TEMPLATE_TAG[key]
            chosen = pick(entries, lambda e, tag=tag: tag in e["tags"])
        ids = [e["id"] for e in chosen]
        templates[key] = ids
        if not ids:
            pool = by_tag.get(TEMPLATE_TAG.get(key) or "", [])
            gaps[key] = {
                "reason": "没有 asrScore≥0.6 的可用段" if pool else "该标签没有任何段",
                "tag": TEMPLATE_TAG.get(key),
                "candidates": len(pool),
            }

    templates["soft"] = list(templates.get("comfort", []))
    if not templates["soft"]:
        gaps["soft"] = {"reason": "随 comfort 一起空", "tag": "comfort", "candidates": 0}

    # §2 断言：comfort 必须有段，否则停在这里并把诊断贴回来
    if not templates.get("comfort"):
        hits = [e for e in entries
                if COMFORT_WORDS.search(str(e.get("text", "")) + " " + str(e.get("asrText", "")))]
        diag = [{"id": e["id"], "text": e["text"], "usable": e["usable"],
                 "asrScore": e["asrScore"]} for e in hits[:10]]
        raise SystemExit(
            "STOP：comfort 直选命中 0 条（usable 且 asrScore≥0.6）。"
            f"文本命中 {len(hits)} 条，前 10 条诊断：{diag}"
        )
    return templates, gaps


def main() -> int:
    old = read_json(OLD / "catalog.json")
    old_ids = [c["id"] for c in old["clips"]]
    next_id = max(int(i[1:]) for i in old_ids) + 1

    rows = read_tags()
    pins = load_pins(STAGE)
    metas = {k: read_json(NORMALIZED / k / "meta.json") for k in SOURCE_KEYS}
    indexes = {k: {c["id"]: c for c in read_json(SLICES / k / "clips" / "index.json")["clips"]}
               for k in SOURCE_KEYS}

    STAGE.mkdir(parents=True, exist_ok=True)
    clips_dir = STAGE / "clips"
    if clips_dir.exists():
        for old_file in clips_dir.glob("*.ogg"):
            old_file.unlink()
    clips_dir.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    allocated, next_id = allocate(rows, old, next_id, pins)
    entries, failures = [], []

    for row, clip_id in allocated:
        index = indexes[row["sourceKey"]][row["id"]]
        start_ms, end_ms = index["sourceStart"], index["sourceEnd"]
        start = max(0.0, (start_ms - HEAD_MS) / 1000)
        dur = (end_ms + TAIL_MS) / 1000 - start
        fade_out = max(0.0, dur - FADE_OUT_MS / 1000)
        target = clips_dir / f"{clip_id}.ogg"
        cmd = [
            FFMPEG, "-y", "-v", "error",
            "-ss", f"{start:.3f}", "-i", str(NORMALIZED / row["sourceKey"] / SOURCE_WAV),
            "-t", f"{dur:.3f}",
            "-af", (f"afade=t=in:st=0:d={FADE_MS / 1000},"
                    f"afade=t=out:st={fade_out:.3f}:d={FADE_OUT_MS / 1000}"),
            "-c:a", "libopus", "-b:a", BITRATE, "-ar", "48000", "-ac", "1",
            str(target),
        ]
        if _run_to_log(cmd, LOGS / "05-encode.log") != 0:
            failures.append({"id": clip_id, "sourceKey": row["sourceKey"], "reason": "encode-failed"})
            continue

        meta = metas[row["sourceKey"]]
        entries.append({
            "id": clip_id,
            "sourceKey": row["sourceKey"],
            "stem": STEM,
            "text": row["text"],
            "file": f"clips/{clip_id}.ogg",
            "duration": round(dur, 3),
            "sourceStart": round(start, 3),
            "sourceEnd": round(start + dur, 3),
            "tags": row["tags"],
            "asrText": row["text"],
            "asrScore": round(row["asrScore"], 3),
            "usable": row["usable"],
            "textSource": "asr",
            "sourceFingerprint": {
                "sourceKey": row["sourceKey"],
                "bvid": meta["bvid"],
                "sourceSha256": meta["sourceSha256"],
                "startMs": index["sourceStart"],
                "endMs": index["sourceEnd"],
                "energyStartMs": index.get("energyStart", index["sourceStart"]),
                "energyEndMs": index.get("energyEnd", index["sourceEnd"]),
                "sliceIndex": row["id"],
                "emotion": row.get("emotion", ""),
            },
        })

    entries.sort(key=lambda e: e["id"])
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"STOP：catalog id 重号 {dup[:5]}")

    # P0.2：pinned 段必须在，且各出现一次；缺一个就不写 catalog
    present = set(ids)
    missing = [pid for pid in pins["ids"] if pid not in present]
    if missing:
        raise SystemExit(f"STOP：pinned id 缺失 {missing}，不写 catalog")
    if len(pins["ids"]) != len(set(pins["ids"])):
        raise SystemExit("STOP：pinned id 本身有重复")

    files = {p.name for p in clips_dir.glob("*.ogg")}
    if len(files) != len(entries):
        raise SystemExit(f"STOP：文件数 {len(files)} != catalog 条目 {len(entries)}")

    write_json(STAGE / "catalog.json", {
        "version": 2,
        "source": "bilibili:BV1C5s6zaE3P,BV1wt2jBwE4p,BV1fQzSBMEbs",
        "clips": entries,
    })

    templates, unmapped = build_templates(entries)
    write_json(STAGE / "templates.json", {"version": 2, "templates": templates})
    write_json(STAGE / "templates-unmapped.json", unmapped)

    # P1.2：选不出段的键也要落到 missing-intents 里（04 刚写过，这边追加一段）
    gaps_path = TAGGED / "missing-intents.json"
    if gaps_path.exists():
        report = read_json(gaps_path)
        report["templateGaps"] = unmapped
        report["templateKeys"] = {k: len(v) for k, v in templates.items()}
        write_json(gaps_path, report)
    else:
        write_json(gaps_path, {"templateGaps": unmapped,
                               "templateKeys": {k: len(v) for k, v in templates.items()}})

    by_id = {e["id"]: e for e in entries}
    reused = sum(1 for e in entries if e["id"] in set(old_ids))
    usable = sum(1 for e in entries if e["usable"])
    print(f"catalog v2：{len(entries)} 条（沿用旧 id {reused}，新分配 {len(entries) - reused}，"
          f"下一个号 c{next_id:04d}）")
    print(f"usable {usable}（{usable / len(entries) * 100:.1f}%）  编码失败 {len(failures)}")
    for key, ids_ in templates.items():
        detail = "、".join(f"{cid}「{by_id[cid]['text'][:14]}」{by_id[cid]['duration']:.2f}s"
                          for cid in ids_) or "（空）"
        print(f"  {key:<9} {detail}")
    if unmapped:
        print(f"留空/异常：{list(unmapped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
