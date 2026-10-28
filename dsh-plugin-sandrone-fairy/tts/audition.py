"""Bake the same attitude line with every reference clip for A/B listening."""

import json
import os
import subprocess
import time
import urllib.request

import numpy as np
import soundfile as sf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(BASE, "tts", "ref")
OUT_DIR = os.path.join(BASE, "preview")
FFMPEG = r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe"
API = "http://127.0.0.1:9880/tts"

TEXT = "哼，才不是特意等你。……不过既然你回来了，我就勉强陪你一会儿。"


def synth(text, ref):
    payload = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": ref.replace("\\", "/"),
        "prompt_text": "",
        "prompt_lang": "zh",
        "text_split_method": "cut5",
        "batch_size": 1,
        "speed_factor": 0.95,
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


def stats(path):
    data, rate = sf.read(path, dtype="float32")
    mono = data if data.ndim == 1 else data.mean(axis=1)
    rms = float(np.sqrt((mono ** 2).mean()))
    frame = 1024
    peaks = []
    for start in range(0, max(0, len(mono) - frame), frame * 2):
        chunk = mono[start:start + frame]
        if float(np.abs(chunk).mean()) < 0.01:
            continue
        spec = np.correlate(chunk, chunk, "full")[frame - 1:]
        spec = spec / (spec[0] + 1e-9)
        peaks.append(float(spec[40:400].max()) if len(spec) > 400 else 0.0)
    return rms, float(np.mean(peaks)) if peaks else 0.0


def main():
    rows = []
    for index in range(1, 7):
        ref = os.path.join(REF_DIR, "line%d.wav" % index)
        if not os.path.exists(ref):
            continue
        wav = os.path.join(OUT_DIR, "va-%d.wav" % index)
        m4a = os.path.join(OUT_DIR, "va-%d.m4a" % index)
        began = time.time()
        audio = synth(TEXT, ref)
        with open(wav, "wb") as handle:
            handle.write(audio)
        duration = sf.info(wav).duration
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", wav, "-c:a", "aac", "-b:a", "96k", m4a],
            check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        rms, pitch = stats(ref)
        rows.append((index, duration, time.time() - began, rms, pitch, os.path.getsize(m4a) // 1024))
        os.remove(wav)
        print("va-%d: audio %.2fs took %.1fs ref_rms %.3f ref_liveliness %.2f %dKB"
              % (index, duration, time.time() - began, rms, pitch, rows[-1][5]), flush=True)

    print("")
    print("liveliness ranking (higher = more ups and downs):")
    for row in sorted(rows, key=lambda item: -item[4]):
        print("  ref line%d: liveliness %.2f  rms %.3f  synth %.2fs"
              % (row[0], row[4], row[3], row[1]))


if __name__ == "__main__":
    main()
