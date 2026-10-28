"""Does prompt_text actually change the prosody?

Zero-shot with an empty prompt_text only carries the speaker embedding (timbre).
Supplying the reference transcript lets the semantic model condition on content,
which is where the pitch/rhythm of the reference comes from.
Same output sentence, same reference, one knob.
"""

import json
import os
import subprocess
import urllib.request

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "http://127.0.0.1:9880/tts"
REF = os.path.join(ROOT, "tts", "ref", "line4.wav")
TEXT = "……哼，回来了。我又没在等你。"
PROMPT = "上次是聊到你在……帮哥伦比亚找回了名字什么的，他听完脸都红了。"
OUT = os.path.join(ROOT, "preview", "ref-demo")


def synth(prompt_text, name):
    payload = {
        "text": TEXT, "text_lang": "zh",
        "ref_audio_path": REF.replace("\\", "/"),
        "prompt_text": prompt_text, "prompt_lang": "zh",
        "top_k": 15, "top_p": 1, "temperature": 1,
        "text_split_method": "cut5", "batch_size": 1,
        "speed_factor": 0.95, "media_type": "wav", "streaming_mode": False,
    }
    req = urllib.request.Request(API, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = resp.read()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with open(path, "wb") as fh:
        fh.write(raw)
    return path


def stats(path):
    import librosa
    a, sr = sf.read(path, always_2d=False)
    if a.ndim > 1:
        a = a.mean(axis=1)
    a = a.astype(np.float32)
    a = a / (np.max(np.abs(a)) or 1.0)
    f0, _, _ = librosa.pyin(a, fmin=70, fmax=420, sr=sr, frame_length=1024, hop_length=256)
    f0 = f0[np.isfinite(f0)]
    hop = int(0.02 * sr)
    frames = max(1, len(a) // hop)
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(frames)])
    db = 20 * np.log10(rms + 1e-12)
    spec = np.abs(librosa.stft(a, n_fft=1024, hop_length=256))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=1024)
    e = spec.mean(axis=1)
    return {
        "dur": len(a) / sr,
        "f0_mean": float(np.mean(f0)),
        "f0_std": float(np.std(f0)),
        "f0_range": float(np.percentile(f0, 95) - np.percentile(f0, 5)),
        "erg_std": float(np.std(db)),
        "cen": float((freqs * e).sum() / (e.sum() + 1e-9)),
        "hf": float(e[freqs > 4000].sum() / (e.sum() + 1e-9)),
    }


if __name__ == "__main__":
    empty = synth("", "pt-empty")
    full = synth(PROMPT, "pt-full")
    print(f"{'':<10}{'dur':>6}{'f0mean':>8}{'f0std':>7}{'f0rng':>7}{'ergstd':>7}{'cen':>7}{'hf':>7}")
    for name, path in [("空 prompt", empty), ("带文本", full)]:
        s = stats(path)
        print(f"{name:<10}{s['dur']:>6.2f}{s['f0_mean']:>8.1f}{s['f0_std']:>7.1f}"
              f"{s['f0_range']:>7.1f}{s['erg_std']:>7.2f}{s['cen']:>7.0f}{s['hf']:>7.3f}")
