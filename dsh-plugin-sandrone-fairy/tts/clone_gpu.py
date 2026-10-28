import argparse
import os
import sys
import time
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "engine" / "CosyVoice-main"
MODELS = ROOT / "engine" / "models" / "models" / "iic--CosyVoice2-0.5B" / "snapshots" / "master"
DEFAULT_MODEL = MODELS
DEFAULT_REF = ROOT / "ref" / "line2.wav"

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "third_party" / "Matcha-TTS"))

import soundfile as sf
import torch

_orig_load = torch.load


def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _patched_load


def load_wav(path, target_sr):
    if torch.is_tensor(path):
        return path
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    wav = torch.from_numpy(data.T)
    if wav.dim() == 2 and wav.size(0) > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != target_sr:
        import torchaudio.functional as F

        wav = F.resample(wav, sr, target_sr)
    return wav


import cosyvoice.utils.file_utils as _fu
import cosyvoice.cli.frontend as _fe

_fu.load_wav = load_wav
_fe.load_wav = load_wav

from cosyvoice.cli.cosyvoice import CosyVoice2

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def build(fp16=None):
    if fp16 is None:
        fp16 = DEVICE == "cuda"
    t0 = time.time()
    cosy = CosyVoice2(str(DEFAULT_MODEL), load_jit=False, load_trt=False, fp16=fp16)
    if DEVICE == "cuda":
        try:
            cosy.model.llm.to("cuda")
            cosy.model.flow.to("cuda")
            cosy.model.hift.to("cuda")
        except Exception as exc:  # noqa: BLE001
            print("move-to-cuda failed:", exc, file=sys.stderr)
    return cosy, time.time() - t0


def synth(cosy, text, ref, out, speed=0.92):
    t0 = time.time()
    first = None
    chunks = []
    for item in cosy.inference_cross_lingual(text, ref, stream=True, speed=speed):
        if first is None:
            first = time.time() - t0
        chunks.append(item["tts_speech"])
    audio = torch.cat(chunks, dim=1) if len(chunks) > 1 else chunks[0]
    sf.write(out, audio.squeeze(0).numpy(), cosy.sample_rate)
    return time.time() - t0, first, audio.size(1) / cosy.sample_rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=str(DEFAULT_REF))
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=0.92)
    ap.add_argument("--fp16", default="auto")
    args = ap.parse_args()
    fp16 = None if args.fp16 == "auto" else args.fp16 in ("1", "true", "True")
    cosy, load_s = build(fp16)
    total, first, dur = synth(cosy, args.text, args.ref, args.out, args.speed)
    print(json.dumps({
        "device": DEVICE,
        "fp16": bool(fp16),
        "load": round(load_s, 1),
        "first": round(first, 1) if first else None,
        "total": round(total, 1),
        "audio": round(dur, 2),
        "out": args.out,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
