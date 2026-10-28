"""为「起伏太大 / 人机味太重」的句子各烘一版候选，产出对比试听。

    python tools/ab_fix.py            # 焙全部候选
    python tools/ab_fix.py --list     # 只看会焙哪些

候选配方：
  起伏大（f0_std 高）→ 换 warm 参考音 + 语速 -0.03（收一点，也别太平）
  人机味（f0_std 低、高频少）→ 换 cool 参考音（带 prompt_text，最接近自然陈述）+ 语速 -0.02
"""

import imageio_ffmpeg
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(ROOT, "tts", "ref")
OUT = os.path.join(ROOT, "preview", "ab-fix")
API = os.environ.get("SANDRONE_GS_API", "http://127.0.0.1:9880") + "/tts"
FFMPEG = os.environ.get(
    "SANDRONE_FFMPEG",
    imageio_ffmpeg.get_ffmpeg_exe(),
)
GAIN = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,afade=t=in:st=0:d=0.015,adelay=60:all=1,loudnorm=I=-14:TP=-1.5:LRA=11"

REFS = {
    "cool": ("ref-cool-new.wav", 0.95, "看来这地方没人管不代表不该有人管"),
    "warm": ("ref-warm.wav", 0.92, ""),
    "tease": ("ref-vivid.wav", 0.98, ""),
    "tired": ("ref-soft.wav", 0.90, ""),
}

# key -> (原因, 目标池, 语速调整)
SUSPECTS = {
    "react-flatter": ("起伏大", "warm", -0.03),
    "react-giveup": ("起伏大", "warm", -0.03),
    "react-hello": ("起伏大", "warm", -0.03),
    "react-nightlight": ("起伏大", "tired", -0.02),
    "greet-evening": ("起伏大", "cool", -0.02),
    "idle-dawn": ("起伏大", "cool", -0.02),
    "react-tease": ("人机味", "cool", -0.02),
    "react-overtime": ("人机味", "warm", 0.0),
    "idle-dusk": ("人机味", "warm", 0.0),
    "whisper-gear": ("人机味", "cool", -0.02),
}


def synth(text, ref, speed, prompt):
    payload = {
        "text": text, "text_lang": "zh", "ref_audio_path": ref,
        "prompt_text": prompt, "prompt_lang": "zh",
        "text_split_method": "cut5", "batch_size": 1,
        "speed_factor": speed, "media_type": "wav", "streaming_mode": False,
    }
    req = urllib.request.Request(API, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def main():
    with io.open(os.path.join(ROOT, "tts", "pack.json"), encoding="utf-8") as fh:
        pack = json.load(fh)

    if "--list" in sys.argv:
        for key, (why, pool, delta) in SUSPECTS.items():
            print("%-18s %-6s -> %-5s %+.2f  %s" % (key, why, pool, delta, pack[key]))
        return

    os.makedirs(OUT, exist_ok=True)
    report = []
    for key, (why, pool, delta) in SUSPECTS.items():
        text = pack[key]
        ref_name, base_speed, prompt = REFS[pool]
        ref = os.path.join(REF_DIR, ref_name).replace("\\", "/")
        speed = round(base_speed + delta, 3)
        began = time.time()
        try:
            audio = synth(text, ref, speed, prompt)
        except Exception as error:
            print("[fail]", key, error)
            continue
        wav = os.path.join(OUT, "_" + key + ".wav")
        with open(wav, "wb") as fh:
            fh.write(audio)
        out = os.path.join(OUT, key + ".m4a")
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav, "-af", GAIN,
                        "-c:a", "aac", "-b:a", "128k", out], check=True)
        os.remove(wav)
        report.append({"key": key, "why": why, "pool": pool, "speed": speed, "text": text})
        print("[ok] %-18s %-5s %.2f  %.1fs" % (key, pool, speed, time.time() - began), flush=True)

    io.open(os.path.join(OUT, "report.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps(report, ensure_ascii=False, indent=1))
    print("baked", len(report))


if __name__ == "__main__":
    main()
