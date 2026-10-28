"""零样本声音克隆：把任意文本用「桑多涅」的音色念出来。

用法：
  python clone.py --ref <参考音频.wav> --text "要念的句子" --out out.wav

设计要点：
- 用 CosyVoice2 的 cross-lingual 模式：只需要参考音频、不需要它的文字稿。
- torch>=2.6 的 torch.load 默认 weights_only=True，加载官方权重会失败，这里统一改写。
"""
import argparse
import os
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parent / "engine"
REPO = ENGINE / "CosyVoice-main"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "third_party" / "Matcha-TTS"))

import torch

_orig_load = torch.load


def _patched_load(*args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(*args, **kwargs)


torch.load = _patched_load

import soundfile as sf  # noqa: E402
import torchaudio  # noqa: E402
from cosyvoice.cli.cosyvoice import CosyVoice2  # noqa: E402


def load_wav(path, target_sr=16000):
    if isinstance(path, torch.Tensor):
        return path
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    wav = torch.from_numpy(data.T.copy())
    if sr != target_sr:
        wav = torchaudio.functional.resample(wav, sr, target_sr)
    return wav


import cosyvoice.utils.file_utils as _fu  # noqa: E402
import cosyvoice.cli.frontend as _fe  # noqa: E402

_fu.load_wav = load_wav
_fe.load_wav = load_wav


def save_wav(path, wav, sr):
    arr = wav.squeeze(0).detach().cpu().numpy()
    sf.write(str(path), arr, sr)

DEFAULT_MODEL = ENGINE / "models" / "models" / "iic--CosyVoice2-0.5B" / "snapshots" / "master"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--speed", type=float, default=0.92)
    args = ap.parse_args()

    t0 = time.time()
    cosy = CosyVoice2(args.model, load_jit=False, load_trt=False, fp16=False)
    print(f"[clone] model ready in {time.time() - t0:.1f}s", flush=True)

    prompt = load_wav(args.ref, 16000)
    t1 = time.time()
    n = 0
    for i, chunk in enumerate(
        cosy.inference_cross_lingual(args.text, prompt, stream=False, speed=args.speed)
    ):
        save_wav(args.out if i == 0 else args.out.replace(".wav", f"_{i}.wav"), chunk["tts_speech"], cosy.sample_rate)
        n += 1
    print(f"[clone] synthesized {n} chunk(s) in {time.time() - t1:.1f}s -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
