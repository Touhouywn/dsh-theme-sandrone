"""A/B 抽听包：每源挑 5 条 BGM 最明显的段，original 与 vocals 并排。

挑选依据：该段「安静帧里 <200Hz 能量占比」降序（BGM 在安静处最露）。
输出 01-separate/ab-listen/<源键>/{NN}_{original,vocals}.ogg + 清单 md。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FFMPEG, NORMALIZED, ROOT, SLICES, SOURCE_KEYS, read_json, write_json  # noqa: E402

OUT = ROOT / "01-separate" / "ab-listen"
PICK = 5
FADE_MS = 20


def quiet_low_share(path: Path, start_ms: int, end_ms: int) -> float:
    tmp = ROOT / "logs" / "_ab.pcm"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as fh:
        subprocess.run([FFMPEG, "-v", "error", "-nostdin", "-ss", f"{start_ms / 1000:.3f}",
                        "-t", f"{(end_ms - start_ms) / 1000:.3f}", "-i", str(path),
                        "-f", "s16le", "-ac", "1", "-ar", "48000", "-"],
                       stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    x = np.frombuffer(tmp.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0
    hop = 960
    n = x.size // hop
    if n < 2:
        return 0.0
    blocks = x[: n * hop].reshape(n, hop)
    d = 20 * np.log10(np.sqrt((blocks ** 2).mean(axis=1)) + 1e-9)
    spec = np.abs(np.fft.rfft(blocks * np.hanning(hop), axis=1)) ** 2
    freqs = np.fft.rfftfreq(hop, 1 / 48000)
    low = spec[:, freqs < 200].sum(axis=1)
    total = spec.sum(axis=1)
    quiet = d < float(np.percentile(d, 50))
    if not quiet.any():
        return 0.0
    return float(low[quiet].sum() / max(1e-12, total[quiet].sum()))


def cut(src: Path, target: Path, start_ms: int, end_ms: int) -> bool:
    dur = (end_ms - start_ms) / 1000
    fade_out = max(0.0, dur - FADE_MS / 1000)
    proc = subprocess.run([
        FFMPEG, "-y", "-v", "error", "-ss", f"{start_ms / 1000:.3f}", "-i", str(src),
        "-t", f"{dur:.3f}",
        "-af", (f"afade=t=in:st=0:d={FADE_MS / 1000},"
                f"afade=t=out:st={fade_out:.3f}:d={FADE_MS / 1000}"),
        "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1", str(target),
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return proc.returncode == 0


def main() -> int:
    lines = ["# A/B 抽听包（original vs vocals）", "",
             "每源 5 段，按「安静帧低频占比」降序挑——那是 BGM 最藏不住的地方。",
             "同一段两次切的边界完全一致，只换音源。", ""]
    summary = {}
    for key in SOURCE_KEYS:
        src = NORMALIZED / key / "source.wav"
        voc = NORMALIZED / key / "source-vocals.wav"
        segs = read_json(SLICES / key / "segments.json")["segments"]
        if not voc.exists() or not segs:
            continue
        scored = []
        for seg in segs:
            share = quiet_low_share(src, seg["start"], seg["end"])
            scored.append((share, seg))
        scored.sort(key=lambda x: -x[0])
        picks = scored[:PICK]

        outdir = OUT / key
        outdir.mkdir(parents=True, exist_ok=True)
        for old in outdir.glob("*"):
            old.unlink()
        lines += [f"## {key}", "", "| # | 段 | 时长 | pre 低频占比 | 文件 |",
                  "| --- | --- | ---: | ---: | --- |"]
        rows = []
        for i, (share, seg) in enumerate(picks, start=1):
            name_o = f"{i:02d}_original.ogg"
            name_v = f"{i:02d}_vocals.ogg"
            ok_o = cut(src, outdir / name_o, seg["start"], seg["end"])
            ok_v = cut(voc, outdir / name_v, seg["start"], seg["end"])
            dur = (seg["end"] - seg["start"]) / 1000
            lines.append(f"| {i} | {seg['start']}–{seg['end']}ms | {dur:.2f}s | "
                         f"{share:.3f} | {name_o if ok_o else '（失败）'} / "
                         f"{name_v if ok_v else '（失败）'} |")
            rows.append({"index": i, "startMs": seg["start"], "endMs": seg["end"],
                         "duration": round(dur, 3), "preLowShare": round(share, 4),
                         "original": name_o if ok_o else None,
                         "vocals": name_v if ok_v else None})
        lines.append("")
        summary[key] = rows

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "listen.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(OUT / "index.json", {"pickPerSource": PICK, "items": summary})
    print(f"写了 {OUT / 'listen.md'}")
    for key, rows in summary.items():
        print(f"  {key}: {len(rows)} 段")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
