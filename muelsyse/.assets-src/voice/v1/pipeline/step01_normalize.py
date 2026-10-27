"""01 normalize：原始整轨 -> 48k 母带 + 16k 工作轨 + meta + sha256。

只读 sources/*.m4a；产出写 00-normalized/<源键>/。
16k 工作轨由 voicekit wav 生成（后续 vad/cut/asr 都只认它）；
48k 母带由 ffmpeg loudnorm 单遍生成（05 建库编码时作为音源）。

冒烟：python step01_normalize.py [源键 ...]
全跑：python step01_normalize.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    FFMPEG,
    LOGS,
    NORMALIZED,
    SOURCE_KEYS,
    SOURCES,
    _run_to_log,
    hashed,
    max_volume,
    probe,
    voicekit,
    write_json,
)

LOUDNORM = "loudnorm=I=-18:TP=-1.5:LRA=11"
DUR_TOL = 0.1  # 秒，±0.1 容差
PEAK_MAX = -1.5  # dBFS


def run_one(key: str) -> dict:
    bvid, title = SOURCE_KEYS[key]
    src = SOURCES / f"{bvid}.m4a"
    if not src.exists():
        raise SystemExit(f"[{key}] 缺素材：{src}")
    out = NORMALIZED / key
    out.mkdir(parents=True, exist_ok=True)
    log = LOGS / key

    src_meta = probe(src, log / "01-probe-source.log")
    dur = src_meta["duration"]
    if not dur:
        raise SystemExit(f"[{key}] 探测不到源时长")
    if src_meta["sampleRate"] != "待标" and src_meta["sampleRate"] < 32000:
        src_meta["qualityNote"] = "源采样率 <32k，音质结论下调"

    # 48k 母带（听感/建库音源）
    master = out / "source.wav"
    code = _run_to_log(
        [FFMPEG, "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1",
         "-ar", "48000", "-af", LOUDNORM, "-c:a", "pcm_s24le", str(master)],
        log / "01-master.log",
    )
    if code != 0:
        raise SystemExit(f"[{key}] 48k 母带转码失败，见 {log / '01-master.log'}")

    # 16k 工作轨（voicekit 契约格式，vad/cut/asr 唯一入口）
    work = out / "source-16k.wav"
    code = voicekit(["wav", str(src), str(work)], log / "01-wav16k.log")
    if code != 0:
        raise SystemExit(f"[{key}] voicekit wav 失败，见 {log / '01-wav16k.log'}")

    status = []
    dur_master = probe(master, log / "01-probe-master.log")["duration"]
    dur_work = probe(work, log / "01-probe-work.log")["duration"]
    for label, got in (("48k", dur_master), ("16k", dur_work)):
        delta = abs((got or 0) - dur)
        status.append({"check": f"duration-{label}", "expect": f"{dur:.3f}±{DUR_TOL}",
                       "actual": got, "ok": delta <= DUR_TOL})

    peak_master = max_volume(master, log / "01-peak-master.log")
    peak_work = max_volume(work, log / "01-peak-work.log")
    for label, pk in (("48k", peak_master), ("16k", peak_work)):
        status.append({"check": f"peak-{label}", "expect": f"<={PEAK_MAX}",
                       "actual": pk, "ok": pk is not None and pk <= PEAK_MAX})

    payload = {
        "sourceKey": key,
        "bvid": bvid,
        "title": title,
        "sourceFile": str(src),
        "sourceSha256": hashed(src),
        "sourceBytes": src.stat().st_size,
        "probe": src_meta,
        "files": {
            "master48k": {"path": str(master), "bytes": master.stat().st_size, "loudnorm": LOUDNORM},
            "work16k": {"path": str(work), "bytes": work.stat().st_size},
        },
        "checks": status,
        "ok": all(c["ok"] for c in status),
    }
    write_json(out / "meta.json", payload)
    (out / "source.sha256").write_text(
        f"{payload['sourceSha256']}  {src.name}\n", encoding="utf-8"
    )
    return payload


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    bad = 0
    for key in keys:
        p = run_one(key)
        failed = [c for c in p["checks"] if not c["ok"]]
        print(f"[{key}] {p['title']}")
        print(f"  src {p['probe']['duration']}s  {p['probe']['codec']} "
              f"{p['probe']['sampleRate']}Hz {p['probe']['channels']}ch")
        for c in failed:
            print(f"  FAIL {c['check']}: expect {c['expect']} actual {c['actual']}")
        if not p["ok"]:
            bad += 1
    print(f"done {len(keys) - bad}/{len(keys)} ok")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
