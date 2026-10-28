import sys, time, json
from pathlib import Path

TTS = Path(__file__).resolve().parent
ROOT = TTS.parent
REPO = TTS / "engine" / "CosyVoice-main"
MODELS = TTS / "engine" / "models" / "models" / "iic--CosyVoice2-0.5B" / "snapshots" / "master"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "third_party" / "Matcha-TTS"))

import soundfile as sf
import torch

_o = torch.load
torch.load = lambda *a, **k: _o(*a, **{**k, "weights_only": False})


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

print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("free/total before:", [round(x / 1024 ** 3, 2) for x in torch.cuda.mem_get_info()])

t0 = time.time()
cosy = CosyVoice2(str(MODELS), load_jit=False, load_trt=False, fp16=True)
print("loaded in", round(time.time() - t0, 1), "s")

for name in ("llm", "flow", "hift"):
    mod = getattr(cosy.model, name, None)
    if mod is None:
        continue
    try:
        mod.to("cuda")
        dev = next(mod.parameters()).device
        print(name, "->", dev)
    except Exception as exc:
        print(name, "move failed:", type(exc).__name__, str(exc)[:160])

if torch.cuda.is_available():
    print("free/total after move:", [round(x / 1024 ** 3, 2) for x in torch.cuda.mem_get_info()])
print("llm dtype:", next(cosy.model.llm.parameters()).dtype)

ref = str(TTS / "ref" / "line2.wav")
text = "欢迎回来，主人。"
t1 = time.time()
first = None
chunks = []
for item in cosy.inference_cross_lingual(text, ref, stream=True, speed=0.94):
    if first is None:
        first = round(time.time() - t1, 2)
        print("first chunk at", first, "s")
    chunks.append(item["tts_speech"])
audio = torch.cat(chunks, dim=1) if len(chunks) > 1 else chunks[0]
print(json.dumps({"first": first, "total": round(time.time() - t1, 2), "audio": round(audio.size(1) / cosy.sample_rate, 2)}))
sf.write(str(ROOT / "preview" / "gpu_probe.wav"), audio.squeeze(0).cpu().numpy(), cosy.sample_rate)
