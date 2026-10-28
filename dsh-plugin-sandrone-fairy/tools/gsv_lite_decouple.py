"""验证「音色 / 风格」是否真的解耦。

对 2 个音色 × 4 种风格合成同一句话，然后比较：
  - 同一音色下换风格：声纹应保持（相似度高）
  - 换音色：声纹应明显变化（相似度低）
  - 同一音色下，风格应改变韵律（f0 标准差 / 时长不同）

用法：
  tts\\gsvenv\\Scripts\\python.exe tools\\gsv_lite_decouple.py --api http://127.0.0.1:9882
"""

from __future__ import annotations

import argparse
import io
import json
import os
import urllib.request
import wave

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "preview", "gsv-lite", "decouple")
TEXT = "雪，茶凉了，我去换一杯。"
TIMBRES = ["sandrone", "alt-a"]
STYLES = ["cool", "warm", "tease", "tired"]


def post(api: str, path: str, payload: dict) -> bytes:
    req = urllib.request.Request(
        api.rstrip("/") + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as res:
        return res.read()


def read_wav(blob: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(blob), "rb") as f:
        sr = f.getframerate()
        data = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return data, sr


def mfcc(x: np.ndarray, sr: int, n: int = 13) -> np.ndarray:
    """手搓 MFCC 均值向量：分帧 → 功率谱 → mel 滤波 → log → DCT。"""
    frame, hop = int(0.025 * sr), int(0.010 * sr)
    if len(x) < frame:
        return np.zeros(n, dtype=np.float32)
    count = 1 + (len(x) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(count)[:, None]
    frames = x[idx] * np.hamming(frame)[None, :]
    spec = np.abs(np.fft.rfft(frames, n=512)) ** 2
    # mel 滤波（26 个三角）
    def hz2mel(f):
        return 2595 * np.log10(1 + f / 700.0)

    def mel2hz(m):
        return 700 * (10 ** (m / 2595.0) - 1)

    n_filt = 26
    mel_pts = np.linspace(hz2mel(60), hz2mel(sr / 2), n_filt + 2)
    bins = np.floor((512 + 1) * mel2hz(mel_pts) / sr).astype(int)
    fb = np.zeros((n_filt, 257), dtype=np.float32)
    for i in range(n_filt):
        lo, mid, hi = bins[i], bins[i + 1], bins[i + 2]
        if hi <= mid or mid <= lo:
            continue
        fb[i, lo:mid] = (np.arange(lo, mid) - lo) / float(mid - lo)
        fb[i, mid:hi] = (hi - np.arange(mid, hi)) / float(hi - mid)
    mel = np.log(spec @ fb.T + 1e-8)
    dct = np.cos(np.pi / n_filt * (np.arange(n_filt)[None, :] + 0.5) * np.arange(n)[:, None])
    return (mel @ dct.T).mean(axis=0)


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def verify(api: str, a: str, b: str) -> float:
    req = urllib.request.Request(
        api.rstrip("/") + "/verify",
        data=json.dumps({"a": a, "b": b}, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as res:
        return float(json.loads(res.read())["score"])


def f0_stats(x: np.ndarray, sr: int) -> tuple[float, float]:
    frame, hop = int(0.040 * sr), int(0.020 * sr)
    vals = []
    for start in range(0, max(1, len(x) - frame), hop):
        seg = x[start:start + frame]
        if np.sqrt(np.mean(seg ** 2)) < 0.01:
            continue
        seg = seg - seg.mean()
        corr = np.correlate(seg, seg, mode="full")[frame - 1:]
        lo, hi = int(sr / 500), int(sr / 70)
        if hi >= len(corr):
            continue
        peak = lo + int(np.argmax(corr[lo:hi]))
        if corr[peak] / (corr[0] + 1e-9) > 0.3:
            vals.append(sr / peak)
    if not vals:
        return 0.0, 0.0
    arr = np.array(vals, dtype=np.float32)
    return float(np.median(arr)), float(np.std(arr))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:9882")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    feats, meta = {}, {}
    for timbre in TIMBRES:
        for style in STYLES:
            blob = post(args.api, "/infer", {"text": TEXT, "pool": style, "timbre": timbre})
            name = f"{timbre}-{style}"
            path = os.path.join(OUT, name + ".wav")
            with open(path, "wb") as f:
                f.write(blob)
            audio, sr = read_wav(blob)
            feats[name] = mfcc(audio, sr)
            f0m, f0s = f0_stats(audio, sr)
            meta[name] = {
                "seconds": round(len(audio) / sr, 2),
                "f0": round(f0m, 1),
                "f0std": round(f0s, 1),
                "rms": round(float(np.sqrt(np.mean(audio ** 2))), 4),
            }
            print(f"[{name}] {meta[name]}")

    names = list(feats)
    matrix = {a: {b: round(cos(feats[a], feats[b]), 3) for b in names} for a in names}

    sv = {}
    for a in names:
        for b in names:
            if a >= b:
                continue
            again = os.path.join(OUT, a + ".wav")
            bpath = os.path.join(OUT, b + ".wav")
            sv[f"{a}|{b}"] = verify(args.api, again, bpath)
    print("[sv] " + json.dumps(sv, ensure_ascii=False))

    intra, inter = [], []
    for key, score in sv.items():
        a, b = key.split("|")
        same = a.split("-")[0] == b.split("-")[0]
        (intra if same else inter).append(score)

    report = {
        "text": TEXT,
        "meta": meta,
        "matrix": matrix,
        "sv": sv,
        "intra_timbre": {"min": min(intra), "mean": round(sum(intra) / len(intra), 3)},
        "inter_timbre": {"max": max(inter), "mean": round(sum(inter) / len(inter), 3)},
        "separated": bool(min(intra) > max(inter)),
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: report[k] for k in ("intra_timbre", "inter_timbre", "separated")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
