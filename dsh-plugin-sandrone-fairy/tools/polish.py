"""精修两条台词：welcome-back（过于妖艳）、react-praise（起伏过大 + 电子音）。

对每条烘 4 个候选：不同参考音池 × 语速 × 温度，量 f0 标准差 / 4kHz 以上占比 /
谱平坦度，再拼一条「原版 + 4 候选」的对比音频。
"""

import imageio_ffmpeg
import io
import json
import os
import subprocess
import sys
import wave

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.environ.get("SANDRONE_GS_API", "http://127.0.0.1:9880")
OUT = os.path.join(BASE, "preview", "polish")

POOLS = {
    "cool": {"file": "ref-cool-new.wav", "text": "看来这地方没人管不代表不该有人管"},
    "warm": {"file": "ref-warm.wav", "text": ""},
    "tease": {"file": "ref-vivid.wav", "text": ""},
    "tired": {"file": "ref-soft.wav", "text": ""},
}

# (名称, 池, 语速, 温度)
CANDIDATES = [
    ("a-cool-095", "cool", 0.95, 0.85),
    ("b-cool-090", "cool", 0.90, 0.80),
    ("c-warm-090", "warm", 0.90, 0.85),
    ("d-tired-088", "tired", 0.88, 0.80),
]

TARGETS = {
    "welcome-back": "回来了。……茶凉了，我重泡一杯。",
    "react-praise": "夸我也没用。……不过，你说得不算难听。",
}


def synth(text, pool, speed, temperature, out_path):
    ref = POOLS[pool]
    body = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": os.path.join(BASE, "tts", "ref", ref["file"]),
        "prompt_text": ref["text"],
        "prompt_lang": "zh",
        "top_k": 15,
        "top_p": 0.95,
        "temperature": temperature,
        "text_split_method": "cut5",
        "speed_factor": speed,
        "media_type": "wav",
        "streaming_mode": False,
        "repetition_penalty": 1.35,
        "fragment_interval": 0.3,
        "seed": 12345,
    }
    tmp = out_path + ".json"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(body, ensure_ascii=False))
    subprocess.run(
        ["curl.exe", "-s", "-o", out_path, "-X", "POST",
         "--data-binary", "@" + tmp, "-H", "content-type: application/json",
         "--max-time", "180", API + "/tts"],
        check=False,
    )
    os.remove(tmp)
    return os.path.getsize(out_path) if os.path.exists(out_path) else 0


def load(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return sr, data.astype(np.float32) / 32768.0


def stats(path):
    sr, x = load(path)
    if len(x) < sr // 10:
        return None
    # 只取有声段（能量高于 -45 dBFS 的 30ms 帧）
    hop, win = int(0.01 * sr), int(0.03 * sr)
    frames = [x[i:i + win] for i in range(0, len(x) - win, hop)]
    rms = np.array([np.sqrt(np.mean(f ** 2) + 1e-12) for f in frames])
    db = 20 * np.log10(rms + 1e-12)
    voiced = [f for f, d in zip(frames, db) if d > -45]
    if len(voiced) < 20:
        return None
    # f0：自相关，60–500 Hz
    lo, hi = int(sr / 500), int(sr / 60)
    f0s = []
    for f in voiced[::2]:
        seg = f * np.hanning(len(f))
        ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
        if ac[0] <= 0:
            continue
        lo_i, hi_i = lo, min(hi, len(ac) - 1)
        if hi_i <= lo_i:
            continue
        lag = lo_i + int(np.argmax(ac[lo_i:hi_i]))
        f0s.append(sr / lag)
    f0s = np.array(f0s)
    f0s = f0s[(f0s > 60) & (f0s < 500)]
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    tot = spec.sum() + 1e-9
    hf = spec[freqs > 4000].sum() / tot
    floor = np.exp(np.mean(np.log(spec + 1e-9)))
    flat = floor / (spec.mean() + 1e-9)
    return {
        "dur": round(len(x) / sr, 2),
        "f0_mean": round(float(np.mean(f0s)), 1) if len(f0s) else 0,
        "f0_std": round(float(np.std(f0s)), 1) if len(f0s) else 0,
        "f0_p10_90": round(float(np.percentile(f0s, 90) - np.percentile(f0s, 10)), 1) if len(f0s) else 0,
        "hf": round(float(hf) * 100, 1),
        "flat": round(float(flat), 3),
        "peak": round(float(np.max(np.abs(x))), 3),
    }


def to_wav32(src, dst):
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-ac", "1", "-ar", "32000", "-c:a", "pcm_s16le", dst],
        check=False,
    )


def concat(files, out_path):
    listfile = out_path + ".txt"
    with io.open(listfile, "w", encoding="utf-8") as fh:
        for p in files:
            fh.write("file '" + p.replace("\\", "/") + "'\n")
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
         "-safe", "0", "-i", listfile, "-c:a", "aac", "-b:a", "128k", out_path],
        check=False,
    )
    os.remove(listfile)


FF = imageio_ffmpeg.get_ffmpeg_exe()


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    report = []
    for key, text in TARGETS.items():
        if only and key != only:
            continue
        old = os.path.join(BASE, "assets", "voice", key + ".m4a")
        print("== %s  %s" % (key, text))
        seq = []
        base_stats = None
        if os.path.exists(old):
            old_wav = os.path.join(OUT, key + "-old.wav")
            to_wav32(old, old_wav)
            base_stats = stats(old_wav)
            seq.append(old_wav)
        print("   原版: %s" % json.dumps(base_stats, ensure_ascii=False))
        for name, pool, speed, temp in CANDIDATES:
            wav = os.path.join(OUT, "%s-%s.wav" % (key, name))
            n = synth(text, pool, speed, temp, wav)
            st = stats(wav) if n else None
            print("   %-12s pool=%-5s speed=%.2f T=%.2f -> %s" % (name, pool, speed, temp, json.dumps(st, ensure_ascii=False)))
            report.append({"key": key, "cand": name, "pool": pool, "speed": speed,
                           "temperature": temp, "bytes": n, "stats": st})
            if st:
                seq.append(wav)
        if seq:
            out = os.path.join(OUT, "%s-候选对比.m4a" % key)
            concat(seq, out)
            print("   -> %s" % out)
    io.open(os.path.join(OUT, "report.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=2))
    print("done")


if __name__ == "__main__":
    main()
