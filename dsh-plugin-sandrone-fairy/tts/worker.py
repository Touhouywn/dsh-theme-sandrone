"""常驻克隆语音工：模型只加载一次，之后逐行读 JSON 合成。

用法（由宿主 index.js 拉起，不手动运行）：
  python worker.py <ref.wav> <cache_dir>
每行输入  {"id": "abc", "text": "要念的话", "speed": 0.9}
每行输出  {"id": "abc", "ok": 1, "ms": 1234}  或  {"id": "abc", "ok": 0, "error": "..."}
音频写 <cache_dir>/abc.wav（24kHz 单声道）。
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clone  # noqa: E402  复用它的 torch.load / load_wav 补丁
import torch  # noqa: E402
from cosyvoice.cli.cosyvoice import CosyVoice2  # noqa: E402


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    ref = sys.argv[1]
    cache = Path(sys.argv[2])
    cache.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    cosy = CosyVoice2(str(clone.DEFAULT_MODEL), load_jit=False, load_trt=False, fp16=False)
    prompt = clone.load_wav(ref, 16000)
    emit({"ready": 1, "ms": int((time.time() - t0) * 1000)})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as error:  # noqa: BLE001
            emit({"ok": 0, "error": f"bad json: {error}"})
            continue

        job_id = str(req.get("id") or "")
        text = (req.get("text") or "").strip()
        if not job_id or not text:
            emit({"id": job_id, "ok": 0, "error": "empty"})
            continue

        started = time.time()
        try:
            speed = float(req.get("speed") or 0.9)
            pieces = [
                chunk["tts_speech"]
                for chunk in cosy.inference_cross_lingual(text, prompt, stream=False, speed=speed)
            ]
            wav = torch.cat(pieces, dim=1) if len(pieces) > 1 else pieces[0]
            out = cache / f"{job_id}.wav"
            clone.save_wav(out, wav, cosy.sample_rate)
            emit({"id": job_id, "ok": 1, "ms": int((time.time() - started) * 1000), "file": out.name})
        except Exception as error:  # noqa: BLE001
            emit({"id": job_id, "ok": 0, "error": str(error)[:200]})


if __name__ == "__main__":
    main()
