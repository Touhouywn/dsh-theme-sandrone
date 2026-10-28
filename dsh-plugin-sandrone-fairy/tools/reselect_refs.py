"""重选参考音：按「韵律起伏」从原始语料里切候选，再配准确原文。

上一轮的教训：语义贴但韵律平的参考音，会把输出压平（13/14 句变差）。
所以这次先按韵律排序，再在「起伏最大的那批」里挑语义合适的，最后配 prompt_text。

产物：tts/ref/ref-{cool,warm,tease,tired}.wav + tts/ref/pool_refs.json + 候选清单
"""

import io
import json
import os
import subprocess

import numpy as np
import soundfile as sf
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "tts", "rvc", "sandrone40k.wav")
REF_DIR = os.path.join(ROOT, "tts", "ref")
CAND_DIR = os.path.join(ROOT, "tts", "ref", "cand")
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR_OUT = 32000
WIN_MIN, WIN_MAX = 3.4, 6.0
TOP_N = 36


def load_corpus():
    import librosa
    audio, sr = sf.read(CORPUS, always_2d=False)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)
    if sr != SR_OUT:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SR_OUT)
    peak = np.max(np.abs(audio)) or 1.0
    return audio / peak


def speech_spans(audio, sr=SR_OUT, thr_db=-34.0, min_gap=0.32, min_len=2.6):
    hop = int(0.01 * sr)
    n = len(audio) // hop
    rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms + 1e-12)
    voiced = db > thr_db
    spans, start, gap = [], None, 0
    for i, flag in enumerate(voiced):
        if flag:
            if start is None:
                start = i
            gap = 0
        elif start is not None:
            gap += 1
            if gap * 0.01 > min_gap:
                spans.append((start * hop, (i - gap) * hop))
                start = None
    if start is not None:
        spans.append((start * hop, n * hop))
    return [(a, b) for a, b in spans if (b - a) / sr >= min_len]


def prosody(seg, sr=SR_OUT):
    import librosa
    f0, _, _ = librosa.pyin(seg, fmin=70, fmax=420, sr=sr, frame_length=1024, hop_length=256)
    f0 = f0[np.isfinite(f0)]
    hop = int(0.02 * sr)
    n = max(1, len(seg) // hop)
    rms = np.array([np.sqrt(np.mean(seg[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms + 1e-12)
    return {
        "f0_mean": float(np.mean(f0)) if len(f0) else 0.0,
        "f0_std": float(np.std(f0)) if len(f0) else 0.0,
        "f0_range": float(np.percentile(f0, 95) - np.percentile(f0, 5)) if len(f0) else 0.0,
        "erg_std": float(np.std(db)),
    }


def transcribe(paths):
    import whisper
    model = whisper.load_model("small", device="cpu")
    out = {}
    for p in paths:
        audio, sr = sf.read(p, always_2d=False)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype(np.float32)
        if sr != 16000:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        r = model.transcribe(audio, language="zh", beam_size=1, condition_on_previous_text=False)
        out[p] = r["text"].strip()
    return out


def main():
    os.makedirs(CAND_DIR, exist_ok=True)
    audio = load_corpus()
    print(f"语料 {len(audio)/SR_OUT:.0f}s")
    spans = speech_spans(audio)
    print(f"语音段 {len(spans)} 个")

    cands = []
    for begin, end in spans:
        dur = (end - begin) / SR_OUT
        if dur < WIN_MIN:
            continue
        # 从长段里滑一个窗口，取起伏最大的位置
        best = None
        step = int(0.4 * SR_OUT)
        width = int(min(WIN_MAX, dur) * SR_OUT)
        for off in range(0, max(1, int(end - begin - width)) + step, step):
            seg = audio[begin + off:begin + off + width]
            if len(seg) < width:
                break
            st = prosody(seg)
            score = st["f0_std"] * 0.6 + st["f0_range"] * 0.25 + st["erg_std"] * 0.15
            if best is None or score > best[0]:
                best = (score, begin + off, st)
        if best:
            cands.append({"score": best[0], "offset": best[1], "dur": width / SR_OUT, **best[2]})

    cands.sort(key=lambda c: -c["score"])
    top = cands[:TOP_N]
    print(f"候选 {len(cands)}，取前 {len(top)}")

    paths = []
    for i, c in enumerate(top):
        seg = audio[c["offset"]:c["offset"] + int(c["dur"] * SR_OUT)]
        path = os.path.join(CAND_DIR, f"c{i:02d}.wav")
        sf.write(path, seg, SR_OUT)
        c["path"] = path
        paths.append(path)

    texts = transcribe(paths)
    for c in top:
        c["text"] = texts.get(c["path"], "")

    with io.open(os.path.join(REF_DIR, "candidates.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump([{k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.items()} for c in top],
                  fh, ensure_ascii=False, indent=2)

    print(f"\n{'#':<4}{'score':>7}{'dur':>6}{'f0std':>7}{'f0rng':>7}{'erg':>6}  文本")
    for i, c in enumerate(top[:24]):
        print(f"{i:<4}{c['score']:>7.1f}{c['dur']:>6.2f}{c['f0_std']:>7.1f}{c['f0_range']:>7.1f}"
              f"{c['erg_std']:>6.1f}  {c['text'][:26]}")


if __name__ == "__main__":
    main()
