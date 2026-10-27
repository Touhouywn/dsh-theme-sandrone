"""分离指标（定稿口径）-> 01-separate/floor-drop.json。

每源记录：
  preP5 / postP5              整轨 P5 帧 RMS（存档，不参与判定）
  preP5Active / postP5Active  只在有声帧（> p50-40dB）里取 P5 —— BGM 藏在低位
  preLowShare                 <200Hz 能量占比（判断有没有 BGM 可去）
  applicable                  preLowShare ≥ 0.15
  dropDb                      preP5Active - postP5Active
  verdict                     applicable ? (dropDb ≥ 3 ? pass : fail) : not_applicable

not_applicable 也保留 preLowShare，用来证明不是拍脑袋。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT  # noqa: E402

FF = (r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"
      r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe")
KEYS = ["youngbranch"]
OUT = ROOT / "01-separate" / "floor-drop.json"
BGM_LOW_SHARE = 0.15
MIN_DROP_DB = 3.0


def measure(path: Path) -> dict:
    tmp = ROOT / "logs" / "_sepstat.pcm"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as fh:
        subprocess.run([FF, "-v", "error", "-nostdin", "-i", str(path),
                        "-f", "s16le", "-ac", "1", "-ar", "48000", "-"],
                       stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    x = np.frombuffer(tmp.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0
    hop = 960
    n = x.size // hop
    blocks = x[: n * hop].reshape(n, hop)
    rms = np.sqrt((blocks ** 2).mean(axis=1))
    d = 20 * np.log10(rms + 1e-9)
    p50 = float(np.percentile(d, 50))
    active = d[d > p50 - 40]

    spec = np.abs(np.fft.rfft(blocks * np.hanning(hop), axis=1)) ** 2
    freqs = np.fft.rfftfreq(hop, 1 / 48000)
    low = spec[:, freqs < 200].sum(axis=1)
    total = spec.sum(axis=1)
    quiet = d < p50  # 只有安静的那些帧才看得见 BGM

    return {
        "p5": round(float(np.percentile(d, 5)), 2),
        "p5Active": round(float(np.percentile(active, 5)), 2) if active.size else None,
        # lowShare 的定义：安静帧里 <200Hz 能量占全带的比例。
        # 「整轨低频占比」会被语音本身的基频淹没（实测三源都在 0.01–0.03），
        # 只有挑出安静帧，BGM 才露出来（v3 0.333 vs v1 0.048 / v2 0.039）。
        "lowShare": round(float(low[quiet].sum() / max(1e-12, total[quiet].sum())), 4),
    }


def main() -> int:
    items = {}
    for key in KEYS:
        src = ROOT / "00-normalized" / key / "source.wav"
        voc = ROOT / "00-normalized" / key / "source-vocals.wav"
        if not voc.exists():
            print(f"{key}: 缺 source-vocals.wav，跳过")
            continue
        a, b = measure(src), measure(voc)
        applicable = a["lowShare"] >= BGM_LOW_SHARE
        drop = (a["p5Active"] - b["p5Active"]) if a["p5Active"] and b["p5Active"] else None
        if not applicable:
            verdict = "not_applicable"
        elif drop is not None and drop >= MIN_DROP_DB:
            verdict = "pass"
        else:
            verdict = "fail"
        items[key] = {
            "preP5": a["p5"], "postP5": b["p5"],
            "preP5Active": a["p5Active"], "postP5Active": b["p5Active"],
            "preLowShare": a["lowShare"], "postLowShare": b["lowShare"],
            "applicable": applicable,
            "dropDb": round(drop, 2) if drop is not None else None,
            "verdict": verdict,
        }
        print(f"{key:<14} preLowShare {a['lowShare']:.4f} applicable={applicable} "
              f"p5Active {a['p5Active']} -> {b['p5Active']} (drop {items[key]['dropDb']}) "
              f"=> {verdict}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"frameMs": 20, "bgmLowShare": BGM_LOW_SHARE,
                               "minDropDb": MIN_DROP_DB, "items": items},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写了 {OUT}")
    bad = [k for k, v in items.items() if v["verdict"] == "fail"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
