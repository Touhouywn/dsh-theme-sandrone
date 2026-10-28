"""Rebuild the SoVITS dataset from the longer, cleaner RVC voice material.

Same slicing rules as build_dataset.py, but the source / output directory are
command line arguments so the old 179 s dataset stays intact.

Usage:
    python tts/build_dataset2.py                 # slice only (CPU, fast)
    python tts/build_dataset2.py --asr           # slice + whisper (needs GPU)
    python tts/build_dataset2.py --asr-only      # transcribe clips already on disk
"""

import argparse
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tts.build_dataset import slice_audio, write_clips  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SRC = os.path.join(BASE, "tts", "rvc", "sandrone40k.wav")
DEFAULT_OUT = os.path.join(BASE, "tts", "dataset2")


def transcribe(rows, device):
    import librosa
    import whisper

    model = whisper.load_model("small", device=device)
    kept = []
    for index, row in enumerate(rows):
        data, rate = sf.read(row["path"], dtype="float32")
        mono = data if data.ndim == 1 else data.mean(axis=1)
        if rate != 16000:
            mono = librosa.resample(mono, orig_sr=rate, target_sr=16000)
        result = model.transcribe(
            mono.astype("float32"), language="zh", fp16=(device == "cuda"),
            beam_size=1, condition_on_previous_text=False,
        )
        text = result.get("text", "").strip()
        bare = "".join(ch for ch in text if ch not in "，。！？、；：…—～,.!?;:")
        if len(bare) < 4:
            os.remove(row["path"])
            continue
        row["text"] = text
        kept.append(row)
        if index % 20 == 0:
            print("  asr %d/%d %s" % (index, len(rows), text[:36]), flush=True)
    return kept


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=DEFAULT_SRC)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--asr", action="store_true")
    parser.add_argument("--asr-only", action="store_true")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    wavs = os.path.join(args.out, "wavs")
    os.makedirs(wavs, exist_ok=True)

    import tts.build_dataset as base

    base.OUT = wavs

    if args.asr_only:
        names = sorted(name for name in os.listdir(wavs) if name.endswith(".wav"))
        rows = [{"path": os.path.join(wavs, name)} for name in names]
        print("asr-only: %d clips" % len(rows), flush=True)
    else:
        data, rate = sf.read(args.src, dtype="float32")
        mono = data if data.ndim == 1 else data.mean(axis=1)
        if rate != base.SR:
            import librosa

            mono = librosa.resample(mono, orig_sr=rate, target_sr=base.SR)
            print("resampled %d -> %d" % (rate, base.SR), flush=True)
        regions = slice_audio(mono)
        print("regions: %d (%.1fs source)" % (len(regions), len(mono) / base.SR), flush=True)
        rows = write_clips(mono, regions)
        print("clips: %d (%.1fs speech)" % (
            len(rows),
            sum(sf.info(r["path"]).duration for r in rows),
        ), flush=True)

    if args.asr or args.asr_only:
        rows = transcribe(rows, args.device)
        print("kept: %d" % len(rows), flush=True)

    with open(os.path.join(args.out, "list.txt"), "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            text = row.get("text") or ""
            handle.write("%s|Sandrone|zh|%s\n" % (os.path.abspath(row["path"]).replace("\\", "/"), text))
    print("list: %s (%d rows)" % (os.path.join(args.out, "list.txt"), len(rows)), flush=True)


if __name__ == "__main__":
    main()
