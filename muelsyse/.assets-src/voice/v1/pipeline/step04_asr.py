"""04 asr：切片目录 -> 转写结果（voicekit asr，一源一个进程）。

只读 01-slices/<源键>/clips/{*.wav,index.json}，产出 02-asr/<源键>.json。

约束（skill 里写明）：一次传一个目录，不逐段开进程；每源冷启动 40–60 秒。
SenseVoice 的 text 里会残留情绪 emoji，这里清出一个 textClean 供打标用，
raw 原样保留，不丢证据。
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, LOGS, SLICES, SOURCE_KEYS, read_json, voicekit, write_json  # noqa: E402

KEEP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]")


def clean(text: str) -> str:
    """只留汉字/字母/数字。标点、空格、emoji、声学标签一律去掉。"""
    text = unicodedata.normalize("NFKC", text or "")
    return "".join(KEEP.findall(text))


def run_one(key: str) -> dict:
    clips = SLICES / key / "clips"
    index = read_json(clips / "index.json")["clips"]
    out = ASR / f"{key}.json"
    code = voicekit(["asr", str(clips), str(out)], LOGS / key / "04-asr.log")
    if code != 0:
        raise SystemExit(f"[{key}] voicekit asr 失败，见 logs/{key}/04-asr.log")
    if not out.exists():
        raise SystemExit(f"[{key}] asr 没产出 {out}")

    payload = read_json(out)
    by_name = {row["file"]: row for row in payload["items"]}
    items, empty = [], []
    for clip in index:
        row = by_name.get(clip["file"])
        if row is None:
            items.append({**clip, "raw": None, "text": "", "textClean": "", "missing": True})
            empty.append(clip["id"])
            continue
        text_clean = clean(row["text"])
        if not text_clean:
            empty.append(clip["id"])
        items.append({
            "id": clip["id"],
            "file": clip["file"],
            "duration": clip["duration"],
            "sourceStart": clip["sourceStart"],
            "sourceEnd": clip["sourceEnd"],
            "raw": row["raw"],
            "text": row["text"],
            "textClean": text_clean,
        })

    write_json(out, {
        "sourceKey": key,
        "model": payload.get("model"),
        "clips": len(index),
        "transcribed": len(index) - len(empty),
        "emptyText": len(empty),
        "emptyIds": empty,
        "items": items,
    })
    return {
        "key": key,
        "clips": len(index),
        "got": len(index) - len(empty),
        "empty": len(empty),
        "chars": sum(len(i["textClean"]) for i in items),
    }


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    for key in keys:
        s = run_one(key)
        print(f"[{s['key']}] {s['got']}/{s['clips']} 条有文本  空 {s['empty']}  "
              f"共 {s['chars']} 字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
