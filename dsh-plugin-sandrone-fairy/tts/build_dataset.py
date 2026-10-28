"""Slice the full voice-over into training clips and transcribe them.

Output: tts/dataset/wavs/*.wav (32k mono) + tts/dataset/list.txt
        (GPT-SoVITS format: path|speaker|lang|text)

Usage:
    python tts/build_dataset.py            # slice + transcribe
    python tts/build_dataset.py --asr-only # reuse clips already on disk
"""

import json
import os
import sys

import numpy as np
import soundfile as sf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "tts", "dataset", "full32k.wav")
OUT = os.path.join(BASE, "tts", "dataset", "wavs")
LIST = os.path.join(BASE, "tts", "dataset", "list.txt")

SR = 32000
MIN_LEN = 1.8
MAX_LEN = 10.0
PAD = 0.10
SIL_DB = -32.0
MIN_GAP = 0.30


def speech_regions(mono):
    frame, hop = 800, 400
    frames = 1 + max(0, (len(mono) - frame) // hop)
    rms = np.empty(frames, dtype=np.float32)
    for i in range(frames):
        chunk = mono[i * hop:i * hop + frame]
        rms[i] = float(np.sqrt((chunk ** 2).mean() + 1e-12))
    active = 20.0 * np.log10(rms + 1e-9) > SIL_DB

    raw = []
    index = 0
    while index < len(active):
        if not active[index]:
            index += 1
            continue
        start = index
        while index < len(active) and active[index]:
            index += 1
        raw.append([start * hop / SR, index * hop / SR])

    merged = []
    for region in raw:
        if merged and region[0] - merged[-1][1] < MIN_GAP:
            merged[-1][1] = region[1]
        else:
            merged.append(region)
    return merged


def slice_audio(mono):
    regions = []
    for start, end in speech_regions(mono):
        if end - start < MIN_LEN:
            continue
        cursor = start
        while end - cursor > MAX_LEN:
            lo = int((cursor + MAX_LEN * 0.55) * SR)
            hi = int((cursor + MAX_LEN) * SR)
            window = np.abs(mono[lo:hi])
            if len(window) < 1600:
                break
            cut = int(np.argmin(window)) + lo
            regions.append([cursor, cut / SR])
            cursor = cut / SR
        if end - cursor >= MIN_LEN:
            regions.append([cursor, end])
    return regions


def write_clips(mono, regions):
    for name in os.listdir(OUT):
        if name.endswith(".wav"):
            os.remove(os.path.join(OUT, name))
    rows = []
    for index, (start, end) in enumerate(regions):
        lo = max(0, int((start - PAD) * SR))
        hi = min(len(mono), int((end + PAD) * SR))
        clip = mono[lo:hi].copy()
        peak = float(np.abs(clip).max())
        if peak < 0.02:
            continue
        clip *= 0.89 / peak
        path = os.path.join(OUT, "%04d.wav" % index)
        sf.write(path, clip, SR, subtype="PCM_16")
        rows.append({"path": path})
    return rows


def transcribe(rows):
    import librosa
    import whisper

    model = whisper.load_model("small", device="cuda")
    kept = []
    for index, row in enumerate(rows):
        data, rate = sf.read(row["path"], dtype="float32")
        mono = data if data.ndim == 1 else data.mean(axis=1)
        if rate != 16000:
            mono = librosa.resample(mono, orig_sr=rate, target_sr=16000)
        result = model.transcribe(
            mono.astype("float32"), language="zh", fp16=True,
            beam_size=1, condition_on_previous_text=False,
        )
        text = result.get("text", "").strip()
        bare = "".join(ch for ch in text if ch not in "，。！？、；：…—～,.!?;:")
        if len(bare) < 4:
            os.remove(row["path"])
            continue
        row["text"] = text
        kept.append(row)
        if index % 25 == 0:
            print("  asr %d/%d %s" % (index, len(rows), text), flush=True)
    return kept


def main():
    asr_only = "--asr-only" in sys.argv
    os.makedirs(OUT, exist_ok=True)

    if asr_only:
        names = sorted(name for name in os.listdir(OUT) if name.endswith(".wav"))
        rows = [{"path": os.path.join(OUT, name)} for name in names]
        print("asr-only: %d clips on disk" % len(rows))
    else:
        data, rate = sf.read(SRC, dtype="float32")
        assert rate == SR, rate
        mono = data if data.ndim == 1 else data.mean(axis=1)
        regions = slice_audio(mono)
        print("regions: %d (%.1fs source)" % (len(regions), len(mono) / SR))
        rows = write_clips(mono, regions)
        print("clips: %d (%.1fs)" % (
            len(rows), sum(sf.info(row["path"]).duration for row in rows)))

    kept = transcribe(rows)
    with open(LIST, "w", encoding="utf-8", newline="\n") as handle:
        for row in kept:
            handle.write("%s|Sandrone|zh|%s\n" % (row["path"].replace("\\", "/"), row["text"]))

    total = sum(sf.info(row["path"]).duration for row in kept)
    print(json.dumps({"clips": len(kept), "seconds": round(total, 1), "list": LIST}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
