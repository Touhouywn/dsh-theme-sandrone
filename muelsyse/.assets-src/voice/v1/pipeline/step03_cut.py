"""03 cut：按句表切出 16k 切片 + index.json。

为什么不用 voicekit 的 cut：它的 ffmpeg 调用把 -ss/-to 当输出选项，
afade 却按 st=0 的绝对时间戳算，任何不从 0 开始的段，淡出增益在整段都是 0，
于是切出来是纯静音（6 秒的段 peak=0.000，volumedetect -91 dB）。
这里改成输入侧 -ss + -t，淡入淡出按段内相对时间算，语义不变：
头部留 HEAD_MS、尾部留 TAIL_MS、淡入 FADE_IN_MS、淡出 FADE_OUT_MS。

只读 01-slices/<源键>/segments.json + 00-normalized/<源键>/source-16k.wav。
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FFMPEG, LOGS, NORMALIZED, SLICES, SOURCE_KEYS, _run_to_log, read_json, write_json  # noqa: E402

HEAD_MS = 80
TAIL_MS = 120
FADE_IN_MS = 5
FADE_OUT_MS = 5
SILENT_DB = -60.0  # 切片峰值低于此判为坏片


def clip_db(path: Path) -> float:
    import numpy as np

    with wave.open(str(path), "rb") as fh:
        raw = fh.readframes(fh.getnframes())
        data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if not len(data):
        return -999.0
    return float(20 * np.log10(abs(data).max() + 1e-9))


def cut_one(wav: Path, segs: list[dict], clips: Path, log: Path) -> tuple[list[dict], list[dict]]:
    """按句表切一批。返回 (index, 静音坏片)。"""
    with wave.open(str(wav), "rb") as fh:
        total_ms = fh.getnframes() / fh.getframerate() * 1000
    clips.mkdir(parents=True, exist_ok=True)
    for old in clips.glob("*.wav"):
        old.unlink()

    index, silent = [], []
    for n, seg in enumerate(segs, start=1):
        start = max(0.0, seg["start"] - HEAD_MS)
        end = min(total_ms, seg["end"] + TAIL_MS)
        dur = (end - start) / 1000
        name = f"c{n:04d}.wav"
        target = clips / name
        fade_out = max(0.0, dur - FADE_OUT_MS / 1000)
        cmd = [
            FFMPEG, "-y", "-v", "error",
            "-ss", f"{start / 1000:.3f}", "-i", str(wav),
            "-t", f"{dur:.3f}",
            "-af", (f"afade=t=in:st=0:d={FADE_IN_MS / 1000},"
                    f"afade=t=out:st={fade_out:.3f}:d={FADE_OUT_MS / 1000}"),
            "-c:a", "pcm_s16le", str(target),
        ]
        code = _run_to_log(cmd, log)
        if code != 0:
            raise SystemExit(f"第 {n} 段切失败，见 {log}")
        peak = clip_db(target)
        if peak < SILENT_DB:
            silent.append({"id": f"c{n:04d}", "peakDb": round(peak, 1),
                           "sourceStart": int(start), "sourceEnd": int(end)})
        index.append({
            "id": f"c{n:04d}", "file": name,
            "sourceStart": int(start), "sourceEnd": int(end),
            "duration": round(dur, 3), "peakDb": round(peak, 1),
        })
    return index, silent


def run_one(key: str) -> dict:
    segs = read_json(SLICES / key / "segments.json")["segments"]
    wav = NORMALIZED / key / "source-16k.wav"
    clips = SLICES / key / "clips"
    index, silent = cut_one(wav, segs, clips, LOGS / key / "03-cut.log")
    write_json(clips / "index.json", {"sourceKey": key, "clips": index})
    durs = [c["duration"] for c in index]
    return {
        "key": key,
        "clips": len(index),
        "totalSeconds": round(sum(durs), 1),
        "min": min(durs) if durs else 0,
        "max": max(durs) if durs else 0,
        "mean": round(sum(durs) / len(durs), 2) if durs else 0,
        "silent": silent,
        "quietest": round(min((c["peakDb"] for c in index), default=0), 1),
    }


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    for key in keys:
        s = run_one(key)
        print(f"[{s['key']}] {s['clips']} clips  {s['totalSeconds']}s  "
              f"{s['min']:.2f}–{s['max']:.2f}s mean {s['mean']}  最轻段 {s['quietest']} dB")
        if s["silent"]:
            print(f"  WARN 静音坏片 {len(s['silent'])}：{s['silent'][:3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
