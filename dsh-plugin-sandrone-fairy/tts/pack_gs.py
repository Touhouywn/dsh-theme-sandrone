"""Bake the fixed Sandrone lines with the trained GPT-SoVITS voice.

每句按「气质」挑参考音：傲娇短句用 vivid、日常用 warm、深夜与低语用 soft。
参考音不同，合出来的底色就不同——这是不改模型也能做出情绪分层的最便宜的办法。

用法：
    python tts/pack_gs.py                 # 全部重焙
    SANDRONE_ONLY=welcome,greet-night python tts/pack_gs.py   # 只焙指定几句
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(BASE, "assets", "voice")
TMP_DIR = os.path.join(BASE, "preview", "tmp_voice")
REF_DIR = os.path.join(BASE, "tts", "ref")
FFMPEG = os.environ.get(
    "SANDRONE_FFMPEG",
    r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe",
)
# 掐掉开头那 100ms 噪声（GPT-SoVITS 冷启动会有），淡入，前置 60ms 静音，再归一
DEFAULT_FILTER = (
    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
    "afade=t=in:st=0:d=0.015,"
    "adelay=60:all=1,"
    "loudnorm=I=-14:TP=-1.5:LRA=11"
)
GAIN_FILTER = os.environ.get("SANDRONE_TTS_FILTER", DEFAULT_FILTER)
API = os.environ.get("SANDRONE_GS_API", "http://127.0.0.1:9880").rstrip("/") + "/tts"

EXTRA = {}  # 台词统一放在 tts/pack.json，避免两处不一致

# 情绪池 → 参考音 / 参考音原文（prompt_text）/ 语速
# prompt_text 必须填：空着只锁音色，韵律会平掉
POOLS = {
    "cool": {"ref": "ref-cool-new.wav", "speed": 0.95,
             "text": "看来这地方没人管不代表不该有人管"},
    "warm": {"ref": "ref-warm.wav", "speed": 0.92, "text": ""},
    "tease": {"ref": "ref-vivid.wav", "speed": 0.98, "text": ""},
    "tired": {"ref": "ref-soft.wav", "speed": 0.90, "text": ""},
}
FALLBACK_REF = "line4.wav"

# 每句属于哪一档（按台词内容手排，改台词时顺手改这里）
POOL_OF = {
    "welcome": "tease",
    "greet-morning": "tease",
    "greet-noon": "tease",
    "greet-afternoon": "warm",
    "greet-evening": "warm",
    "greet-night": "tired",
    "whisper-gear": "tired",
    "whisper-listen": "tired",
    "whisper-rest": "tired",
    "whisper-water": "tired",
    "whisper-idle": "tired",
    "voice-demo": "cool",
    "thinking": "cool",
    "farewell": "warm",

    "react-hello": "cool",
    "react-thanks": "tease",
    "react-tired": "tired",
    "react-night": "tired",
    "react-done": "cool",
    "react-error": "tired",
    "react-praise": "tease",
    "idle-late": "tired",

    "idle-dawn": "warm",
    "idle-noon": "cool",
    "idle-afternoon": "cool",
    "idle-dusk": "cool",
    "idle-long": "tease",
    "welcome-back": "tease",

    "react-wake": "tired",
    "react-overtime": "cool",
    "react-meal": "warm",
    "react-flatter": "tease",
    "react-sorry": "cool",
    "react-fail": "cool",
    "react-win": "tease",
    "react-giveup": "tease",
    "react-nightlight": "warm",
    "react-stretch": "warm",
    "react-sick": "tired",
    "react-comfort": "tired",
    "react-morning": "warm",
    "react-goodnight": "tired",
    "react-busy": "cool",
    "react-agree": "cool",
    "react-curious": "cool",
    "react-tease": "tease",
    "react-rest10": "cool",
    "react-wrapup": "warm",
}
DEFAULT_TIER = "cool"
SPEED_OVERRIDE = {
    "farewell": 0.95,
    "idle-noon": 0.92,
    "react-goodnight": 0.88,
    "react-wake": 0.88,
    "react-morning": 0.95,
    "react-night": 0.88,
    "react-tired": 0.9,
    "react-thanks": 0.88,
    "react-hello": 0.9,
    "whisper-water": 0.9,
    "greet-afternoon": 0.95,
    "greet-morning": 0.95,
    "welcome": 0.92,       # 开屏那句再慢一点，换场更从容
    "welcome-back": 0.98,  # 回家问候按正常对话语速，别逐字
    "react-praise": 0.90,  # 被夸那句压慢一点，去掉甩腔
}


def ref_path(pool):
    info = POOLS.get(pool, POOLS[DEFAULT_TIER])
    path = os.path.join(REF_DIR, info["ref"])
    if not os.path.exists(path):
        path = os.path.join(REF_DIR, FALLBACK_REF)
    return path.replace("\\", "/"), info["speed"], info.get("text", "")


def synth(text, ref, speed, prompt_text):
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": ref,
        "prompt_text": prompt_text,
        "prompt_lang": "zh",
        "text_split_method": "cut5",
        "batch_size": 1,
        "speed_factor": speed,
        "media_type": "wav",
        "streaming_mode": False,
    }
    request = urllib.request.Request(
        API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def main():
    os.makedirs(VOICE_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    with open(os.path.join(BASE, "tts", "pack.json"), encoding="utf-8") as handle:
        lines = json.load(handle)
    lines.update(EXTRA)
    only = {k.strip() for k in (os.environ.get("SANDRONE_ONLY") or "").split(",") if k.strip()}
    if only:
        lines = {k: v for k, v in lines.items() if k in only}
        print("[only] " + ", ".join(sorted(lines)), flush=True)

    failures = 0
    for key, text in lines.items():
        pool = POOL_OF.get(key, DEFAULT_TIER)
        ref, pool_speed, prompt_text = ref_path(pool)
        speed = SPEED_OVERRIDE.get(key, pool_speed)
        wav = os.path.join(TMP_DIR, key + ".wav")
        m4a = os.path.join(VOICE_DIR, key + ".m4a")
        began = time.time()
        try:
            audio = synth(text, ref, speed, prompt_text)
        except Exception as error:
            failures += 1
            print(f"[fail] {key}: {error}", flush=True)
            continue
        with open(wav, "wb") as handle:
            handle.write(audio)
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", wav,
             "-af", GAIN_FILTER, "-c:a", "aac", "-b:a", "128k", m4a],
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        os.remove(wav)
        seconds = time.time() - began
        print(f"[ok] {key:<18} {pool:<6} {os.path.getsize(m4a) // 1024:>4} KB  {seconds:.1f}s  {text}", flush=True)

    print(f"done, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
