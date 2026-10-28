"""逐条量预制台词的「声学画像」，用来找「起伏过大」和「人机味重」的句子。

指标：
  时长 / 起始静音 / 有效段占比 / f0 均值 / f0 标准差 / f0 10-90 分位跨度
  能量标准差 / 4kHz 以上能量占比 / 谱平坦度 / 语速（字/秒）
"""

import imageio_ffmpeg
import io
import json
import os
import re

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.path.join(ROOT, "assets", "voice")

import soundfile as sf


FFMPEG = os.environ.get(
    "SANDRONE_FFMPEG",
    imageio_ffmpeg.get_ffmpeg_exe(),
)


def load(path):
    """m4a 交给 ffmpeg 解码，避免 libsndfile 不认 aac。"""
    if path.lower().endswith((".wav", ".flac")):
        data, sr = sf.read(path, dtype="float32", always_2d=False)
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data, sr

    import subprocess
    out = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "32000", "-"],
                         capture_output=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr.decode("utf-8", "replace")[-400:])
    return np.frombuffer(out.stdout, dtype="<f4").astype("float32"), 32000


def f0_track(x, sr, fmin=70, fmax=420, hop=0.01, win=0.04):
    hop_n, win_n = int(sr * hop), int(sr * win)
    out = []
    for start in range(0, len(x) - win_n, hop_n):
        frame = x[start:start + win_n]
        if np.sqrt(np.mean(frame ** 2)) < 1e-4:
            out.append(np.nan)
            continue
        frame = frame - frame.mean()
        corr = np.correlate(frame, frame, mode="full")[win_n - 1:]
        lo, hi = int(sr / fmax), int(sr / fmin)
        seg = corr[lo:hi]
        if not len(seg) or seg.max() <= 0:
            out.append(np.nan)
            continue
        lag = lo + int(np.argmax(seg))
        out.append(sr / float(lag))
    return np.array(out)


def profile(path):
    x, sr = load(path)
    if sr != 32000:
        # 统一重采样到 32k，保证指标可比
        idx = np.linspace(0, 1, int(len(x) * 32000 / sr), endpoint=False)
        x = np.interp(idx, np.linspace(0, 1, len(x), endpoint=False), x).astype("float32")
        sr = 32000

    dur = len(x) / float(sr)
    frame = int(sr * 0.02)
    rms = np.array([np.sqrt(np.mean(x[i:i + frame] ** 2)) for i in range(0, len(x) - frame, frame)])
    db = 20 * np.log10(np.maximum(rms, 1e-8))
    voiced = db > (db.max() - 26)
    lead = float(np.argmax(voiced) * 0.02) if voiced.any() else 0.0

    f0 = f0_track(x, sr)
    good = f0[~np.isnan(f0)]
    if len(good) > 4:
        lo, hi = np.percentile(good, 10), np.percentile(good, 90)
        f0_mean, f0_std, f0_span = float(np.mean(good)), float(np.std(good)), float(hi - lo)
    else:
        f0_mean = f0_std = f0_span = float("nan")

    # 频谱
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    total = spec.sum() + 1e-12
    hf = float(spec[freqs > 4000].sum() / total)
    p = spec / total
    flat = float(np.exp(np.mean(np.log(p + 1e-12))) / (np.mean(p) + 1e-12))

    return dict(dur=dur, lead=lead, f0_mean=f0_mean, f0_std=f0_std, f0_span=f0_span,
                erg_std=float(np.std(db)), hf=hf, flat=flat)


def main():
    pack = json.loads(io.open(os.path.join(ROOT, "tts", "pack.json"), encoding="utf-8").read())
    rows = []
    for key in sorted(pack):
        path = os.path.join(VOICE, key + ".m4a")
        if not os.path.exists(path):
            continue
        pr = profile(path)
        chars = len(re.sub(r"[^\u4e00-\u9fff]", "", str(pack[key])))
        rows.append((key, chars, pr))

    med_std = float(np.median([r[2]["f0_std"] for r in rows]))
    med_span = float(np.median([r[2]["f0_span"] for r in rows]))
    print("中位 f0_std=%.1f  f0_span=%.1f\n" % (med_std, med_span))
    print("%-16s %4s %5s %5s %6s %6s %6s %6s %6s" % (
        "key", "字", "秒", "起静", "f0均", "f0标", "跨度", "能量标", "高频"))
    for key, chars, pr in rows:
        flag = ""
        if pr["f0_std"] > med_std * 1.45:
            flag = "  ← 起伏大"
        elif pr["f0_std"] < med_std * 0.62:
            flag = "  ← 偏平"
        print("%-16s %4d %5.2f %5.2f %6.0f %6.1f %6.1f %6.1f %6.3f%s" % (
            key, chars, pr["dur"], pr["lead"], pr["f0_mean"], pr["f0_std"],
            pr["f0_span"], pr["erg_std"], pr["hf"], flag))

    out = os.path.join(ROOT, "preview", "clip-profile.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {k: {kk: (None if vv != vv else round(vv, 3)) for kk, vv in pr.items()} for k, _, pr in rows},
        ensure_ascii=False, indent=1))
    print("\n写入", out)


if __name__ == "__main__":
    main()
