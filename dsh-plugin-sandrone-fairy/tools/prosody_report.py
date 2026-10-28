"""Objective prosody stats: how "human" does a TTS take sound?

We cannot listen, so we measure the things humans actually hear as prosody:
  f0 range, energy modulation, pause/breath rate, spectral tilt, HF rolloff.
Run on: their demo, our current clips, and the original game VO (the ceiling).
"""

import glob
import os
import sys

import numpy as np
import soundfile as sf

SR = 32000


def load(path, sr=SR):
    try:
        audio, rate = sf.read(path, always_2d=False)
    except Exception:
        # m4a/AAC 需要 ffmpeg：直接解码到内存
        import subprocess
        ff = os.environ.get("SANDRONE_FFMPEG") or r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe"
        if not os.path.exists(ff):
            import shutil
            ff = shutil.which("ffmpeg") or "ffmpeg"
        raw = subprocess.run([ff, "-v", "quiet", "-i", path, "-f", "f32le", "-ac", "1",
                              "-ar", str(sr), "pipe:1"], capture_output=True).stdout
        audio = np.frombuffer(raw, dtype=np.float32)
        rate = sr
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if rate != sr:
        import librosa
        audio = librosa.resample(audio, orig_sr=rate, target_sr=sr)
    peak = np.max(np.abs(audio)) or 1.0
    return audio / peak


def split_speech(audio, sr=SR, thr_db=-38.0, min_gap=0.28, min_len=0.35):
    hop = int(0.01 * sr)
    frames = len(audio) // hop
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(frames)])
    db = 20 * np.log10(rms + 1e-12)
    voiced = db > thr_db
    spans = []
    start = None
    gap = 0
    for i, flag in enumerate(voiced):
        if flag:
            if start is None:
                start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap * 0.01 > min_gap:
                spans.append((start, i - gap))
                start = None
    if start is not None:
        spans.append((start, len(voiced)))
    out = []
    for a, b in spans:
        if (b - a) * 0.01 >= min_len:
            out.append(audio[a * hop:b * hop])
    return out


def f0_track(seg, sr=SR, fmin=70, fmax=400):
    import librosa
    f0, _, _ = librosa.pyin(seg, fmin=fmin, fmax=fmax, sr=sr, frame_length=1024, hop_length=256)
    return f0[np.isfinite(f0)]


def stats(seg, sr=SR):
    dur = len(seg) / sr
    f0 = f0_track(seg, sr)
    hop = int(0.02 * sr)
    frames = len(seg) // hop
    rms = np.array([np.sqrt(np.mean(seg[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(max(1, frames))])
    rms_db = 20 * np.log10(rms + 1e-12)
    import librosa
    spec = np.abs(librosa.stft(seg, n_fft=1024, hop_length=256))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
    energy = spec.mean(axis=1)
    total = energy.sum() + 1e-9
    hf = energy[freqs > 4000].sum() / total          # 4kHz 以上能量占比（越高越"清楚"，过低=闷=像机器）
    centroid = float((freqs * energy).sum() / total)
    flat = float(np.exp(np.mean(np.log(spec + 1e-9))) / np.mean(spec + 1e-9))
    return {
        "dur": dur,
        "f0_mean": float(np.mean(f0)) if len(f0) else 0.0,
        "f0_std": float(np.std(f0)) if len(f0) else 0.0,
        "f0_p10": float(np.percentile(f0, 10)) if len(f0) else 0.0,
        "f0_p90": float(np.percentile(f0, 90)) if len(f0) else 0.0,
        "f0_range": (float(np.percentile(f0, 90) - np.percentile(f0, 10))) if len(f0) else 0.0,
        "energy_std": float(np.std(rms_db)),
        "hf_ratio": float(hf),
        "centroid": centroid,
        "flatness": flat,
    }


def report(name, segs):
    if not segs:
        print(f"{name:<24} (no speech)")
        return
    rows = [stats(s) for s in segs]
    keys = ["dur", "f0_mean", "f0_std", "f0_range", "energy_std", "hf_ratio", "centroid", "flatness"]
    agg = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    print(f"{name:<24} n={len(rows):<3} "
          + " ".join(f"{k}={agg[k]:6.2f}" for k in keys))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    jobs = []

    demo = os.path.join(root, "preview", "ref-demo", "demo.wav")
    if os.path.exists(demo):
        jobs.append(("他们的 demo 视频", load(demo)))

    clips = sorted(glob.glob(os.path.join(root, "assets", "voice", "*.m4a")))
    for clip in clips[:6]:
        jobs.append(("我们的 " + os.path.basename(clip), load(clip)))

    ref4 = os.path.join(root, "tts", "ref", "line4.wav")
    if os.path.exists(ref4):
        jobs.append(("原声参考 line4", load(ref4)))

    corpus = os.path.join(root, "tts", "rvc", "sandrone40k.wav")
    if os.path.exists(corpus):
        audio = load(corpus)
        segs = split_speech(audio[: 180 * SR])
        if segs:
            jobs.append(("原声语料前 3 分钟", np.concatenate([s for s in segs[:40]])))

    print(f"{'set':<24} {'':<3} " + " ".join(f"{k:>6}" for k in
          ["dur", "f0mean", "f0std", "f0rng", "ergstd", "hf", "cen", "flat"]))
    for name, audio in jobs:
        segs = split_speech(audio)
        report(name, segs)


if __name__ == "__main__":
    main()
