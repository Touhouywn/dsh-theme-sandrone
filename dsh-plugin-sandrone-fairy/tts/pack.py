"""用克隆音色批量生成固定台词，输出 m4a 到 assets/voice/。

模型只加载一次（约 20 秒），之后每句推理 10–40 秒（CPU）。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import clone  # noqa: E402  复用 clone.py 里的补丁与加载逻辑

REF = ROOT / "tts" / "ref" / "line1.wav"
OUT = ROOT / "assets" / "voice"
FFMPEG = Path(r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe")


def main():
    lines = json.loads((ROOT / "tts" / "pack.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or list(lines)

    from cosyvoice.cli.cosyvoice import CosyVoice2

    t0 = time.time()
    cosy = CosyVoice2(str(clone.DEFAULT_MODEL), load_jit=False, load_trt=False, fp16=False)
    print(f"[pack] model ready in {time.time() - t0:.1f}s", flush=True)

    prompt = clone.load_wav(REF, 16000)
    for key in only:
        text = lines[key]
        wav_path = OUT / f"{key}.wav"
        t1 = time.time()
        for i, chunk in enumerate(cosy.inference_cross_lingual(text, prompt, stream=False, speed=0.9)):
            clone.save_wav(wav_path, chunk["tts_speech"], cosy.sample_rate)
            break
        m4a = OUT / f"{key}.m4a"
        subprocess.run(
            [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_path),
             "-c:a", "aac", "-b:a", "96k", str(m4a)],
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        wav_path.unlink(missing_ok=True)
        print(f"[pack] {key} {len(text)}字 {time.time() - t1:.1f}s -> {m4a.name} {m4a.stat().st_size // 1024}KB", flush=True)


if __name__ == "__main__":
    main()
