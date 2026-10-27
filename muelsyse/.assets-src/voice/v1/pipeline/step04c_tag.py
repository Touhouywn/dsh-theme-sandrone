"""04c tag：文本 -> 标签 / usable / 去重 / 意图缺口。

只读：
  01-slices/<源键>/segments.json    （flag=filler）
  02-asr/<源键>.json                （SenseVoice 文本）
  02-asr/<源键>.cross.json          （whisper 互校分 = asrScore）

产出：
  03-tagged/tags.tsv                全部段：id/源/时长/asrScore/usable/标签/文本/去重
  03-tagged/rejected.tsv            去重落败段与原因（音频不删，切片仍留在 01-slices）
  03-tagged/missing-intents.json    E 配额缺口

约定：
- 归一 = NFKC + 去标点空格；opencc 没装（pip 在沙箱里写不进临时目录），
  素材本身是简体，故 t2s 为直通，已在 RULES.md 记明。
- usable = asrScore≥0.55 且 不含名字词 且 0.4–10.2s 且 归一文本 ≥2 字。
- 名字过滤：桑多涅|桑多念|多涅|Sandrone|Marionette → usable=false。
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, SLICES, SOURCE_KEYS, TAGGED, read_json, write_json  # noqa: E402

MIN_SCORE = 0.55
WATCH_SCORE = 0.35
NAME_RE = re.compile(r"桑多涅|桑多念|多涅|Sandrone|Marionette", re.I)
DUR_MIN, DUR_MAX = 0.4, 10.25

# 受控词表（design G）与触发词。顺序有意义：先命中的先落，但允许多标签。
# 触发词宁窄勿宽：误命中的段会把意图模板带偏，缺口由 E 表倒逼，不靠凑。
TRIGGERS: list[tuple[str, str]] = [
    ("greeting", r"你好|您好|早安|早上好|晚上好|很高兴见到|幸会|欢迎|你来了|好久不见"),
    ("farewell", r"再见|拜拜|晚安|告辞|再会|告别"),
    ("thanks", r"谢谢|感谢|多谢|辛苦了|有劳"),
    ("apology", r"抱歉|对不起|不好意思|原谅我|是我的错"),
    ("affirm", r"好的|好啊|可以|没问题|当然|是的|正是|行吧|对的"),
    ("ack", r"嗯|明白了|懂了|收到|原来如此|我知道"),
    ("deny", r"不行|不能|不会|不想|不要|不必|不用|并不是|不是的"),
    ("refuse", r"拒绝|不能说|不方便|不愿意|不该说"),
    ("unsure", r"不确定|也许|可能|大概|或许|说不准|不清楚"),
    ("waiting", r"稍等|等一下|马上|很快就|正在处理|稍后"),
    ("error", r"失败|错误|出错|报错"),
    ("done", r"准备好了|完成了|做好了|我想好了|搞定"),
    ("comfort", r"别急|没事|没关系|慢慢|别担心|不要紧|安心"),
    ("sleep", r"睡|晚安|困了"),
    ("traveler", r"旅行者"),
    ("identity", r"哥伦比娅|哥伦比亚|我是谁|你叫什么|我的名字|我叫"),
    ("moon", r"月亮|月神|月光|月矩|双月|红月|月髓|月色"),
    ("friend", r"朋友|好友|同伴"),
    ("praise", r"厉害|漂亮|聪明|了不起|真棒"),
    ("criticize", r"批评|不满|太差|讨厌|失望|糟透"),
    ("code", r"代码|命令|路径|函数|堆栈|接口|url|http"),
    ("off_topic", r"做梦|梦里|故事|唱歌|旋律|摇篮曲|歌词"),
    ("fact", r"^[0-9一二三四五六七八九十百千万亿]+$"),
]
TAG_VOCAB = {
    "enable", "ack", "soft", "error", "greeting", "farewell", "thanks", "moon",
    "sleep", "friend", "traveler", "apology", "affirm", "deny", "followup",
    "refuse", "unsure", "waiting", "done", "identity", "off_topic", "praise",
    "criticize", "fact", "code", "hum", "filler", "question",
}
# F 意图计数口径统一放 intents.py（04c 与 06 共用，避免两套算法）
from intents import QUOTA, coverage as intent_coverage  # noqa: E402
from intents import is_error_shared, is_error_semantic, load_pins  # noqa: E402

def norm(text: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", unicodedata.normalize("NFKC", text or "")))


EMOTION = re.compile(r"<\|(NEUTRAL|HAPPY|SAD|ANGRY|FEARFUL|DISGUSTED|SURPRISED)\|>")


def tags_for(text: str, raw: str = "") -> list[str]:
    hits = [tag for tag, pattern in TRIGGERS if re.search(pattern, text)]
    # 疑问只看行尾问号或句末「吗/呢」——文本里到处都是「什么」，按词抓会全错
    body = re.sub(r"<\|[^|]*\|>", "", raw or "").strip()
    if re.search(r"[？?]\s*$", body) or re.search(r"(吗|呢)[。？！?!]*$", text):
        hits.append("question")
    return [t for t in hits if t in TAG_VOCAB]


def emotion_of(raw: str) -> str:
    m = EMOTION.search(raw or "")
    return m.group(1).lower() if m else ""


def bucket(duration: float) -> str:
    if duration < 1.5:
        return "<1.5"
    if duration < 3:
        return "1.5-3"
    if duration < 6:
        return "3-6"
    return ">=6"


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0

    def grams(s: str) -> set[str]:
        return {s[i:i + 2] for i in range(max(1, len(s) - 1))}

    ga, gb = grams(a), grams(b)
    dice = 2 * len(ga & gb) / (len(ga) + len(gb)) if (ga or gb) else 0.0
    contain = len(set(a) & set(b)) / max(1, len(set(a)))
    return 0.6 * dice + 0.4 * contain


def load(key: str) -> list[dict]:
    asr = {i["id"]: i for i in read_json(ASR / f"{key}.json")["items"]}
    cross_path = ASR / f"{key}.cross.json"
    if not cross_path.exists():
        raise SystemExit(f"[{key}] 还缺互校结果 {cross_path}，先把 step04b 跑完")
    cross = {i["id"]: i for i in read_json(cross_path)["items"]}
    # segments.json 与 index.json 一一对应：第 i 段 -> c{i+1:04d}
    segs = read_json(SLICES / key / "segments.json")["segments"]
    flags = {f"c{i:04d}": s.get("flag", "") for i, s in enumerate(segs, start=1)}

    rows = []
    for cid, item in asr.items():
        text = item["textClean"]
        raw = item.get("raw") or ""
        score = cross.get(cid, {}).get("asrScore", 0.0)
        name_hit = bool(NAME_RE.search(item["text"]))
        filler = flags.get(cid, "") == "filler"
        tags = tags_for(text, raw)
        if filler:
            tags.append("filler")
        usable = (
            score >= MIN_SCORE
            and not name_hit
            and DUR_MIN <= item["duration"] <= DUR_MAX
            and len(text) >= 2
        )
        rows.append({
            "id": cid,
            "sourceKey": key,
            "duration": item["duration"],
            "asrScore": score,
            "text": text,
            "raw": raw,
            "emotion": emotion_of(raw),
            "tags": sorted(set(tags)),
            "filler": filler,
            "nameHit": name_hit,
            "usable": usable,
            "whisper": cross.get(cid, {}).get("whisper", ""),
        })
    return rows


def dedupe(rows: list[dict], pins: dict) -> list[dict]:
    """归一文本相同；或 asrText 相似 ≥0.9 且时长差 <15% → 留分高者。

    P0.2：pinned 段不参与删除——它就是模板要播的那一段，宁可丢重复的另一条。
    """
    pinned_slices = set(pins["by_slice"])

    def pinned(row: dict) -> bool:
        return (row["sourceKey"], row["id"]) in pinned_slices

    order = sorted(rows, key=lambda r: (not pinned(r), -r["asrScore"], -r["duration"]))
    kept: list[dict] = []
    for row in order:
        match = None
        for other in kept:
            if row["text"] == other["text"]:
                match = other
                break
            if abs(row["duration"] - other["duration"]) / max(other["duration"], 0.01) < 0.15 \
                    and similarity(row["text"], other["text"]) >= 0.9:
                match = other
                break
        if match is None:
            kept.append(row)
            continue
        if pinned(match) and not pinned(row):
            row["dupOf"] = match["id"]
        elif pinned(row) and not pinned(match):
            match["dupOf"] = row["id"]
            kept[kept.index(match)] = row
        else:
            row["dupOf"] = match["id"]
    kept.sort(key=lambda r: (r["sourceKey"], r["id"]))
    return kept


def gap_report(rows: list[dict]) -> dict:
    report = intent_coverage(rows)
    # 对照用：不看标签、只看文本含 error 词的那一档
    for intent in report:
        if intent == "error":
            report[intent]["semanticCount"] = sum(
                1 for r in rows if r["usable"] and is_error_semantic(r))
            report[intent]["sharedIds"] = sorted(
                r["id"] for r in rows if r["usable"] and is_error_shared(r))
    return report


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    pins = load_pins(SLICES.parent / "stage")
    all_rows: list[dict] = []
    for key in keys:
        all_rows.extend(load(key))

    kept = dedupe(all_rows, pins)
    losers = [r for r in all_rows if r.get("dupOf")]
    TAGGED.mkdir(parents=True, exist_ok=True)

    header = "id\tsourceKey\tduration\tasrScore\tusable\ttags\tfiller\tnameHit\temotion\ttext"
    lines = [header]
    for r in kept:
        lines.append("\t".join([
            r["id"], r["sourceKey"], f"{r['duration']:.2f}", f"{r['asrScore']:.3f}",
            "1" if r["usable"] else "0", ",".join(r["tags"]),
            "1" if r["filler"] else "0", "1" if r["nameHit"] else "0",
            r["emotion"], r["text"],
        ]))
    (TAGGED / "tags.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rej = ["id\tsourceKey\tduration\tasrScore\tdupOf\ttext"]
    for r in sorted(losers, key=lambda x: x["id"]):
        rej.append("\t".join([r["id"], r["sourceKey"], f"{r['duration']:.2f}",
                              f"{r['asrScore']:.3f}", r["dupOf"], r["text"]]))
    (TAGGED / "rejected.tsv").write_text("\n".join(rej) + "\n", encoding="utf-8")

    gaps = gap_report(kept)
    write_json(TAGGED / "missing-intents.json", {
        "quota": {level: [{"intent": i, "need": n, "bandsNeed": b} for i, n, b in items]
                  for level, items in QUOTA.items()},
        "intents": gaps,
        "missing": [k for k, v in gaps.items() if not v["ok"]],
    })

    usable = sum(1 for r in kept if r["usable"])
    print(f"总段 {len(all_rows)}  去重后 {len(kept)}  落败 {len(losers)}")
    print(f"usable {usable}（{usable / len(kept) * 100:.1f}%）  "
          f"分<{WATCH_SCORE} {sum(1 for r in kept if r['asrScore'] < WATCH_SCORE)}  "
          f"名字命中 {sum(1 for r in kept if r['nameHit'])}  filler {sum(1 for r in kept if r['filler'])}")
    for level, items in QUOTA.items():
        hit = sum(1 for i, _, _ in items if gaps[i]["ok"])
        print(f"  {level}: {hit}/{len(items)} 达标")
    err = gaps["error"]
    print(f"  error 计入门槛 {err['count']}/{err['need']}  档位 {err['bands']}  "
          f"（§3 字面口径 {err.get('sharedIds', []) and len(err['sharedIds'])} 段）")
    bad = [k for k, v in gaps.items() if not v["ok"]]
    print(f"  缺口：{', '.join(bad) if bad else '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
