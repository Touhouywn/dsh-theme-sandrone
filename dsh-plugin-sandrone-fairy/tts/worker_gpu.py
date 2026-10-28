"""常驻克隆工：模型只加载一次，之后按行读 JSON 请求逐句合成。

stdin  : {"id": "...", "text": "...", "out": "...", "speed": 0.92}
stdout : {"ready": true, "device": "cuda"}
         {"id": "...", "ok": true, "first": 1.2, "total": 2.4, "audio": 3.1}
         {"id": "...", "ok": false, "error": "..."}
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT / "engine" / "CosyVoice-main"
MODELS = ROOT / "engine" / "models" / "models" / "iic--CosyVoice2-0.5B" / "snapshots" / "master"

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


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    ref = str(ROOT / "ref" / "line2.wav")
    force_cpu = os.environ.get("SANDRONE_TTS_DEVICE", "").lower() == "cpu"
    device = "cpu" if force_cpu or not torch.cuda.is_available() else "cuda"
    t0 = time.time()
    cosy = CosyVoice2(str(MODELS), load_jit=False, load_trt=False, fp16=True)
    if device == "cuda":
        # 4GB 显存：权重必须转半精度才装得下，否则会抖到 CPU 上反而更慢
        cosy.model.llm.to("cuda").half()
        cosy.model.flow.to("cuda").half()
        cosy.model.hift.to("cuda")
        decoder = cosy.model.flow.decoder
        forward = decoder.forward

        def fast_decoder(*args, **kwargs):
            kwargs["n_timesteps"] = 8
            return forward(*args, **kwargs)

        decoder.forward = fast_decoder
    emit({"ready": True, "device": device, "fp16": device == "cuda", "load": round(time.time() - t0, 1)})

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            emit({"ok": False, "error": "bad json: %s" % exc})
            continue
        rid = req.get("id") or ""
        text = (req.get("text") or "").strip()
        out = req.get("out") or ""
        speed = float(req.get("speed") or 0.92)
        if not text or not out:
            emit({"id": rid, "ok": False, "error": "missing text/out"})
            continue
        try:
            began = time.time()
            first = None
            chunks = []
            for item in cosy.inference_cross_lingual(text, ref, stream=True, speed=speed):
                if first is None:
                    first = round(time.time() - began, 2)
                chunks.append(item["tts_speech"])
            audio = torch.cat(chunks, dim=1) if len(chunks) > 1 else chunks[0]
            sf.write(out, audio.squeeze(0).numpy(), cosy.sample_rate)
            emit({
                "id": rid,
                "ok": True,
                "first": first,
                "total": round(time.time() - began, 2),
                "audio": round(audio.size(1) / cosy.sample_rate, 2),
            })
        except Exception as exc:  # noqa: BLE001
            emit({"id": rid, "ok": False, "error": str(exc)[:300]})


if __name__ == "__main__":
    main()
