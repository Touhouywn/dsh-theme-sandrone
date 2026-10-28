"""Fair prompt_text test: reference clip WITH its exact transcript.

The earlier attempt used a garbled ASR transcript and produced a 1.3s truncated
clip — garbage in, garbage out. Here the reference comes from our own dataset,
so the transcript is exact.
"""

import json
import os
import urllib.request

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "http://127.0.0.1:9880/tts"
OUT = os.path.join(ROOT, "preview", "ref-demo")
TEXT = "……哼，回来了。我又没在等你。"

# (参考音路径, 参考音原文) —— 来自 tts/dataset/list.txt，文本是准的
CASES = [
    ("tts/dataset/wavs/0062.wav", "你们有兴趣就自己拿杯子帮我把这些茶解决了吧"),
    ("tts/dataset/wavs/0053.wav", "再盯着我也不会给你发茶会邀请函的哥伦比亚"),
]


def synth(ref, prompt_text, name):
    payload = {
        "text": TEXT, "text_lang": "zh",
        "ref_audio_path": ref.replace("\\", "/"),
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
    return (len(a) / sr, float(np.mean(f0)), float(np.std(f0)),
            float(np.percentile(f0, 95) - np.percentile(f0, 5)),
            float(np.std(db)),
            float((freqs * e).sum() / (e.sum() + 1e-9)),
            float(e[freqs > 4000].sum() / (e.sum() + 1e-9)))


if __name__ == "__main__":
    print(f"{'case':<28}{'dur':>6}{'f0mean':>8}{'f0std':>7}{'f0rng':>7}{'ergstd':>7}{'cen':>7}{'hf':>7}")
    for rel, prompt in CASES:
        ref = os.path.join(ROOT, rel)
        if not os.path.exists(ref):
            print("missing", rel)
            continue
        for label, pt in [("空 prompt", ""), ("准确原文", prompt)]:
            try:
                path = synth(ref, pt, f"{os.path.basename(rel)[:-4]}-{'empty' if not pt else 'full'}")
                d, fm, fs, fr, eg, cen, hf = stats(path)
                print(f"{os.path.basename(rel) + ' ' + label:<28}{d:>6.2f}{fm:>8.1f}{fs:>7.1f}{fr:>7.1f}{eg:>7.2f}{cen:>7.0f}{hf:>7.3f}")
            except Exception as exc:
                print(f"{os.path.basename(rel) + ' ' + label:<28} FAILED {exc}")
