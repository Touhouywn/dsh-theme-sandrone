"""看一眼 P5 这个指标到底测到了什么：顺带算百分位与「带内中位数」。

只读 00-normalized/<源键>/{source.wav,source-vocals.wav}，只打印，不写产物。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2")
FF = (r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"
      r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
KEYS = ["v1-training", "v2-story62", "v3-fullvoice"]


def stats(path: Path) -> dict:
    out = ROOT / "logs" / "_sepstat.pcm"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fh:
        subprocess.run([FF, "-v", "error", "-nostdin", "-i", str(path),
                        "-f", "s16le", "-ac", "1", "-ar", "48000", "-"],
                       stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    x = np.frombuffer(out.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0
    hop = 960
    n = x.size // hop
    rms = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    d = 20 * np.log10(rms + 1e-9)

    def q(p):
        return round(float(np.percentile(d, p)), 1)

    band = d[(d > -60) & (d < -20)]
    return {
        "p5": q(5), "p20": q(20), "p50": q(50), "p90": q(90),
        "band_med": round(float(np.median(band)), 1) if band.size else None,
        "band_share": round(band.size / max(1, d.size), 3),
    }


def main() -> int:
    for key in KEYS:
        a = ROOT / "00-normalized" / key / "source.wav"
        b = ROOT / "00-normalized" / key / "source-vocals.wav"
        if not b.exists():
            print(f"{key}: 缺 vocals")
            continue
        A, B = stats(a), stats(b)
        print(key)
        print("  原     ", A)
        print("  vocals ", B)
        print(f"  P5 差 {A['p5'] - B['p5']:+.1f} dB | 带内中位数差 "
              f"{(A['band_med'] - B['band_med']) if A['band_med'] and B['band_med'] else 'n/a'} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
