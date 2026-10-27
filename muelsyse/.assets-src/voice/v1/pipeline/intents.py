"""意图口径：标签映射、配额、error 共享集。04c 与 06 共用这一份，避免两套算法。

配额按修正稿 §4：
- affirm/deny/followup/thanks ≥6 段、3 档
- greeting ≥3 段、2 档；farewell ≥4 段、2 档
- error ≥6 段、3 档 ——「共享集」口径见 §3：deny/refuse/apology/comfort 里
  文本含 不行|不能|无法|失败|错了|出错 的段计入，不给原段加标签。
- 中频 ≥4 段、2 档；低频 ≥3 段、2 档；enable 2 段。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ERROR_WORDS = re.compile(r"不行|不能|无法|失败|错了|出错")
ERROR_HOSTS = {"deny", "refuse", "apology", "comfort"}

# 覆盖率硬下限（P0.2）：这两个意图压线，掉一段就掉出配额
COVERAGE_FLOORS = {"greeting": 3, "farewell": 4}


def load_pins(stage: Path) -> dict:
    """从现有 stage 的 templates.json + catalog.json 读出 pinned 段。

    返回 {"ids": [...], "by_slice": {(sourceKey, sliceIndex): clipId}}。
    04 用 by_slice 保护去重，05 用 by_slice 把 id 钉回原处。
    """
    stage = Path(stage)
    tpl_p, cat_p = stage / "templates.json", stage / "catalog.json"
    if not (tpl_p.exists() and cat_p.exists()):
        return {"ids": [], "by_slice": {}}
    tpl = json.loads(tpl_p.read_text(encoding="utf-8"))["templates"]
    cat = {c["id"]: c for c in json.loads(cat_p.read_text(encoding="utf-8"))["clips"]}
    ids = sorted({i for v in tpl.values() for i in v if i in cat})
    by_slice = {}
    for cid in ids:
        fp = cat[cid].get("sourceFingerprint") or {}
        key = (fp.get("sourceKey"), fp.get("sliceIndex"))
        if key[0] and key[1]:
            by_slice[key] = cid
    return {"ids": ids, "by_slice": by_slice}

INTENT_TAGS = {
    "affirm": ["affirm"], "deny": ["deny"], "followup": ["followup", "question"],
    "refuse": ["refuse"], "unsure": ["unsure"], "waiting": ["waiting"],
    "error": ["error"], "done": ["done"], "greeting": ["greeting"],
    "farewell": ["farewell"], "thanks": ["thanks"], "apology": ["apology"],
    "comfort": ["comfort"], "goodnight": ["sleep"], "traveler": ["traveler"],
    "identity": ["identity"], "off_topic": ["off_topic"], "praise": ["praise"],
    "criticize": ["criticize"], "code": ["code"], "fact": ["fact"],
    "enable": ["enable"], "question": ["question"],
}

QUOTA: dict[str, list[tuple[str, int, int]]] = {
    "high": [
        ("affirm", 6, 3), ("deny", 6, 3), ("followup", 6, 3), ("thanks", 6, 3),
        ("greeting", 3, 2), ("farewell", 4, 2), ("error", 6, 3),
    ],
    "mid": [
        ("refuse", 4, 2), ("unsure", 4, 2), ("waiting", 4, 2), ("done", 4, 2),
        ("apology", 4, 2), ("comfort", 4, 2), ("traveler", 4, 2), ("identity", 4, 2),
    ],
    "low": [
        ("goodnight", 3, 2), ("off_topic", 3, 2), ("praise", 3, 2),
        ("criticize", 3, 2), ("fact", 3, 2), ("question", 3, 2),
    ],
    "enable": [("enable", 2, 1)],
}


def band(duration: float) -> str:
    if duration < 1.5:
        return "<1.5"
    if duration < 3:
        return "1.5-3"
    if duration < 6:
        return "3-6"
    return ">=6"


def is_error_shared(row: dict) -> bool:
    """§3 的 error 共享段：四类标签之一 + 文本含 error 词。"""
    return bool(set(row["tags"]) & ERROR_HOSTS) and bool(ERROR_WORDS.search(row["text"]))


def is_error_semantic(row: dict) -> bool:
    """更宽的一档：只看文本含 error 词，不看标签。用于报告对照，不进门槛。"""
    return bool(ERROR_WORDS.search(row["text"]))


# P1.3：模板键集 = 旧 11 键 ∪ 新 21 表 = 27 键
TEMPLATE_KEYS = [
    "enable", "ack", "soft", "error", "greeting", "farewell", "thanks", "moon",
    "sleep", "friend", "traveler",
    "apology", "affirm", "deny", "followup", "refuse", "unsure", "waiting",
    "done", "comfort", "goodnight", "identity", "off_topic", "praise",
    "criticize", "code", "fact",
]
# 键 -> tags.tsv 里的标签。followup 落到 question，goodnight 落到 sleep；
# error 走 §3 的 literal 集合，comfort 走文本直选，enable/soft 特殊处理。
TEMPLATE_TAG = {
    "code": None, "fact": None, "error": None, "comfort": None,
    "enable": None, "soft": None,
    "ack": "ack", "greeting": "greeting", "farewell": "farewell", "thanks": "thanks",
    "apology": "apology", "affirm": "affirm", "deny": "deny",
    "followup": "question", "refuse": "refuse", "unsure": "unsure",
    "waiting": "waiting", "done": "done", "goodnight": "sleep",
    "traveler": "traveler", "identity": "identity", "moon": "moon",
    "sleep": "sleep", "friend": "friend", "off_topic": "off_topic",
    "praise": "praise", "criticize": "criticize",
}

# comfort 直选（不走 tagger）：文本命中就算
COMFORT_WORDS = re.compile(r"没事|没关系|慢慢|别急|别担心|不要紧|安心")


def template_semantic_ok(key: str, entry: dict) -> bool:
    """模板断言：选中的段，其标签或文本要和键的语义对得上。05 与 06 共用。"""
    tags = set(entry["tags"])
    text = entry["text"]
    if key in ("code", "fact"):
        return True  # 这两键本来就该空
    if key == "error":
        return is_error_shared(entry) or "error" in tags
    if key in ("comfort", "soft"):
        return bool(COMFORT_WORDS.search(text)) or bool(tags & {"comfort", "apology", "unsure"})
    if key == "enable":
        return bool(tags & {"affirm", "ack", "traveler"})
    if key == "ack":
        return bool(tags & {"ack", "affirm"})
    if key in ("sleep", "goodnight"):
        return "sleep" in tags or bool(re.search(r"睡|晚安", text))
    want = TEMPLATE_TAG.get(key)
    return bool(want and want in tags)




def pool(intent: str, rows: list[dict], usable_only: bool = True) -> list[dict]:
    """某意图的候选段。

    error 用「共享口径」：只要文本里出现 不行/不能/无法/失败/错了/出错 就算——§3 列的
    四类标签是个便利清单，不是语义边界（「无法穿过这扇门」这种段没有 deny/refuse 标签，
    但它就是 error 的料）。字面口径（仅四标签）的计数单独报，见 error_shared_count。
    """
    if intent == "error":
        chosen = [r for r in rows if is_error_semantic(r)]
    else:
        tags = INTENT_TAGS[intent]
        chosen = [r for r in rows if set(r["tags"]) & set(tags)]
    if usable_only:
        chosen = [r for r in chosen if r["usable"]]
    return chosen


def error_shared_count(rows: list[dict]) -> int:
    """§3 字面口径的计数，只用于对照报告。"""
    return sum(1 for r in rows if r["usable"] and is_error_shared(r))


def coverage(rows: list[dict]) -> dict:
    report = {}
    for level, items in QUOTA.items():
        for intent, need, bands_need in items:
            chosen = pool(intent, rows)
            bands = {}
            for r in chosen:
                bands[band(r["duration"])] = bands.get(band(r["duration"]), 0) + 1
            report[intent] = {
                "level": level,
                "count": len(chosen),
                "need": need,
                "bands": bands,
                "bandsNeed": bands_need,
                "ok": len(chosen) >= need and len(bands) >= bands_need,
            }
    return report


def high_ok_rate(report: dict) -> float:
    intents = [i for i, _, _ in QUOTA["high"]]
    return sum(1 for i in intents if report[i]["ok"]) / len(intents)
