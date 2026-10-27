"""给 lowShare 找定义：三种候选口径，看哪个跟 0.15 这个门槛对得上。

A. 低频帧占比：<200Hz 能量 > 300–3400Hz 能量的帧数占比
B. 静音帧低频占比：低于 p50 的帧里，低频能量占全带的比例
C. 伴奏低频占比：demucs 的 no_vocals 里，低频能量占全带比例
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2")
FF = (r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"
      r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
KEYS = ["v1-training", "v2-story62", "v3-fullvoice"]


def pcm(path: Path) -> np.ndarray:
    tmp = ROOT / "logs" / "_probe.pcm"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as fh:
        subprocess.run([FF, "-v", "error", "-nostdin", "-i", str(path),
                        "-f", "s16le", "-ac", "1", "-ar", "48000", "-"],
                       stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return np.frombuffer(tmp.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0


def metrics(path: Path) -> dict:
    x = pcm(path)
    hop = 960
    n = x.size // hop
    blocks = x[: n * hop].reshape(n, hop)
    spec = np.abs(np.fft.rfft(blocks * np.hanning(hop), axis=1)) ** 2
    freqs = np.fft.rfftfreq(hop, 1 / 48000)
    low = spec[:, freqs < 200].sum(axis=1)
    mid = spec[:, (freqs >= 300) & (freqs <= 3400)].sum(axis=1)
    total = spec.sum(axis=1)
    rms = np.sqrt((blocks ** 2).mean(axis=1))
    d = 20 * np.log10(rms + 1e-9)
    quiet = d < np.percentile(d, 50)
    return {
        "A_lowFrames": round(float((low > mid).mean()), 4),
        "B_quietLowShare": round(float(low[quiet].sum() / max(1e-12, total[quiet].sum())), 4),
        "C_allLowShare": round(float(low.sum() / max(1e-12, total.sum())), 4),
    }


for key in KEYS:
    print(key)
    for label, name in [("source", "source.wav"), ("vocals", "source-vocals.wav")]:
        print(f"  {label:<7}", metrics(ROOT / "00-normalized" / key / name))
    acc = ROOT / "01-separate" / key / "demucs" / "htdemucs" / "input-stereo" / "no_vocals.wav"
    if acc.exists():
        print("  no_vocals", metrics(acc))
