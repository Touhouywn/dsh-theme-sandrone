"""抽听清单的机器预检：我没法替人听，但能量、边界、削波这些量一遍就能排掉大半。

只读 publish/clips/*.ogg 与 04-audit/listen-checklist.md，
产出 04-audit/listen-triage.md（逐段指标 + 复核标记）。

判据（按听感风险，不按文本）：
  起音  < 20ms 静音 → 可能被切头
  尾音  < 20ms 静音 → 可能被切尾
  peak  ≥ -0.3 dBFS 或 有满刻度样本 → 疑似削波
  rms   < -45 dBFS   → 偏轻
  时长  < 0.6s       → 偏短
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FFMPEG, ROOT, read_json  # noqa: E402

PUBLISH = ROOT / "publish"
AUDIT = ROOT / "04-audit"
TMP = ROOT / "logs" / "_triage"
SR = 48000
FLOOR_DB = -40.0
HEAD_MS = 20
TAIL_MS = 20


def decode(path: Path) -> "object":
    import numpy as np

    TMP.mkdir(parents=True, exist_ok=True)
    out = TMP / "x.pcm"
    import subprocess

    with open(out, "wb") as fh:
        proc = subprocess.run(
            [FFMPEG, "-v", "error", "-nostdin", "-hide_banner", "-i", str(path),
             "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
            stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=30,
        )
    if proc.returncode != 0:
        return None
    data = out.read_bytes()
    return np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0


def db(x: float) -> float:
    import math

    return 20 * math.log10(max(x, 1e-9))


def analyze(path: Path) -> dict | None:
    import numpy as np

    x = decode(path)
    if x is None or x.size == 0:
        return None
    hop = SR // 100  # 10ms
    n = x.size
    peak = float(np.abs(x).max())
    rms = float(np.sqrt((x * x).mean()))
    clipped = int((np.abs(x) >= 0.999).sum())

    frames = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, n - hop + 1, hop)])
    frame_db = 20 * np.log10(frames + 1e-9)
    # 自适应门限：v2-story62 有 BGM，绝对 -40dB 会把底噪当成声音，
    # 所以取「第 10 百分位 + 6dB」，再与 -40dB 取高。
    floor = max(FLOOR_DB, float(np.percentile(frame_db, 10)) + 6)
    loud = frame_db > floor
    if loud.any():
        head = int(np.argmax(loud)) * 10
        last = int(len(loud) - 1 - np.argmax(loud[::-1]))
        tail_ms = max(0.0, n / SR * 1000 - (last * 10 + 10))
    else:
        head, tail_ms = 0, 0.0
    return {
        "seconds": round(n / SR, 3),
        "peakDb": round(db(peak), 1),
        "rmsDb": round(db(rms), 1),
        "clipped": clipped,
        "headSilenceMs": head,
        "tailSilenceMs": round(tail_ms, 1),
    }


def flags(info: dict) -> list[str]:
    out = []
    if info["headSilenceMs"] < HEAD_MS:
        out.append("切头")
    if info["tailSilenceMs"] < TAIL_MS:
        out.append("切尾")
    if info["peakDb"] >= -0.3 or info["clipped"] > 0:
        out.append("削波")
    if info["rmsDb"] < -45:
        out.append("偏轻")
    if info["seconds"] < 0.6:
        out.append("偏短")
    return out


def parse_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    seen, order = set(), []
    for cid in re.findall(r"`(c\d{4})`", text):
        if cid not in seen:
            seen.add(cid)
            order.append(cid)
    return order


def main() -> int:
    ids = parse_ids(AUDIT / "listen-checklist.md")
    catalog = {c["id"]: c for c in read_json(PUBLISH / "catalog.json")["clips"]}
    rows, missing = [], []
    for cid in ids:
        path = PUBLISH / "clips" / f"{cid}.ogg"
        if not path.exists():
            missing.append(cid)
            continue
        info = analyze(path)
        if info is None:
            missing.append(cid)
            continue
        rows.append({"id": cid, "text": catalog[cid]["text"], **info, "flags": flags(info)})

    flagged = [r for r in rows if r["flags"]]
    lines = ["# 抽听清单 · 机器预检", "",
             f"清单里 {len(ids)} 段（唯一 id），实际量了 {len(rows)} 段；"
             f"有标记的 {len(flagged)} 段。", "",
             "标的是**听感风险**，不是文本对错：",
             "- 切头 / 切尾：边界处几乎没有静音，可能切掉辅音或气口",
             "- 削波：峰值到顶或有满刻度样本",
             "- 偏轻 / 偏短：音量或长度不足", "",
             "## 需要优先复核的段", ""]
    if flagged:
        lines += ["| id | text | 时长 | peak | rms | 头静音 | 尾静音 | 标记 |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
        for r in sorted(flagged, key=lambda r: (-len(r["flags"]), r["id"])):
            lines.append(f"| `{r['id']}` | {r['text'][:24]} | {r['seconds']:.2f}s | "
                         f"{r['peakDb']} | {r['rmsDb']} | {r['headSilenceMs']}ms | "
                         f"{r['tailSilenceMs']}ms | {'、'.join(r['flags'])} |")
    else:
        lines.append("没有需要标记的段。")

    lines += ["", "## 全量指标", "",
              "| id | text | 时长 | peak | rms | 头静音 | 尾静音 | 标记 |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in rows:
        lines.append(f"| `{r['id']}` | {r['text'][:24]} | {r['seconds']:.2f}s | {r['peakDb']} | "
                     f"{r['rmsDb']} | {r['headSilenceMs']}ms | {r['tailSilenceMs']}ms | "
                     f"{'、'.join(r['flags']) or '—'} |")
    if missing:
        lines += ["", f"量不了的：{', '.join(missing)}"]

    (AUDIT / "listen-triage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    from collections import Counter

    counts = Counter(f for r in rows for f in r["flags"])
    print(f"量了 {len(rows)} 段，标记 {len(flagged)} 段；{dict(counts)}")
    for r in sorted(flagged, key=lambda r: (-len(r["flags"]), r["id"]))[:15]:
        print(f"  {r['id']} {r['text'][:16]:<18} {r['seconds']:.2f}s "
              f"peak={r['peakDb']} rms={r['rmsDb']} 头{r['headSilenceMs']}ms 尾{r['tailSilenceMs']}ms "
              f"{r['flags']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
