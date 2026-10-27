"""给 voicekit 的转写结果补 id / textClean / 边界（不重新转写）。

voicekit asr 输出只有 {file,duration,raw,text}；04c 需要 id 和 textClean，
这里按 clips/index.json 把两者接上，就地更新 02-asr/<键>.json。
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, SLICES, SOURCE_KEYS, read_json, write_json  # noqa: E402

KEEP = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")


def clean(text: str) -> str:
    return "".join(KEEP.findall(unicodedata.normalize("NFKC", text or "")))


def main(argv: list[str]) -> int:
    for key in argv or list(SOURCE_KEYS):
        path = ASR / f"{key}.json"
        payload = read_json(path)
        if payload.get("items") and "id" in payload["items"][0]:
            print(f"[{key}] 已经有 id，跳过")
            continue
        index = {c["file"]: c for c in read_json(SLICES / key / "clips" / "index.json")["clips"]}
        items, empty = [], []
        for row in payload["items"]:
            clip = index.get(row["file"])
            if clip is None:
                continue
            text_clean = clean(row["text"])
            if not text_clean:
                empty.append(clip["id"])
            items.append({
                "id": clip["id"],
                "file": row["file"],
                "duration": clip["duration"],
                "sourceStart": clip["sourceStart"],
                "sourceEnd": clip["sourceEnd"],
                "raw": row["raw"],
                "text": row["text"],
                "textClean": text_clean,
            })
        items.sort(key=lambda r: r["id"])
        write_json(path, {
            "sourceKey": key,
            "model": payload.get("model"),
            "clips": len(items),
            "transcribed": len(items) - len(empty),
            "emptyText": len(empty),
            "emptyIds": empty,
            "items": items,
        })
        print(f"[{key}] {len(items)} 条，空文本 {len(empty)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
