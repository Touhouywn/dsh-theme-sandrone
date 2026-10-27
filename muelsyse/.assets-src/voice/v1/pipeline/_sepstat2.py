"""P5 的两个替代口径 + 低频占比，看看哪个真的在测 BGM。

- p5_all：整轨 P5（字面口径）
- p5_active：只在「有声帧」（高于 p50-40dB）里取 P5
- low_share：<200Hz 能量占全带的比例（音乐通常低频更重）
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2")
FF = (r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"
      r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
KEYS = ["v1-training", "v2-story62", "v3-fullvoice"]


def frames_of(path: Path) -> np.ndarray:
    out = ROOT / "logs" / "_sepstat.pcm"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        subprocess.run([FF, "-v", "error", "-nostdin", "-i", str(path),
                        "-f", "s16le", "-ac", "1", "-ar", "48000", "-"],
                       stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return np.frombuffer(out.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0


def measure(path: Path) -> dict:
    x = frames_of(path)
    hop = 960
    n = x.size // hop
    blocks = x[: n * hop].reshape(n, hop)
    rms = np.sqrt((blocks ** 2).mean(axis=1))
    d = 20 * np.log10(rms + 1e-9)
    p50 = float(np.percentile(d, 50))
    active = d[d > p50 - 40]
    spec = np.abs(np.fft.rfft(blocks * np.hanning(hop), axis=1)) ** 2
    freqs = np.fft.rfftfreq(hop, 1 / 48000)
    low = spec[:, freqs < 200].sum()
    return {
        "p5_all": round(float(np.percentile(d, 5)), 1),
        "p5_active": round(float(np.percentile(active, 5)), 1) if active.size else None,
        "low_share": round(float(low / max(1e-12, spec.sum())), 4),
    }


for key in KEYS:
    a = measure(ROOT / "00-normalized" / key / "source.wav")
    b = measure(ROOT / "00-normalized" / key / "source-vocals.wav")
    print(key)
    print(f"  p5_all     {a['p5_all']:>7} -> {b['p5_all']:>7}   差 {a['p5_all'] - b['p5_all']:+.1f}")
    if a["p5_active"] and b["p5_active"]:
        print(f"  p5_active  {a['p5_active']:>7} -> {b['p5_active']:>7}   差 {a['p5_active'] - b['p5_active']:+.1f}")
    print(f"  low_share  {a['low_share']:>7} -> {b['low_share']:>7}")
