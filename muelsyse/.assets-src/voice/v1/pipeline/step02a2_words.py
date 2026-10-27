"""02a-words：整轨词级时间戳（faster-whisper，word_timestamps=True）。

02 切分要用「最后一个词的 end」做尾部硬上限，所以词时间戳必须先于切分拿到。
输入 00-normalized/<源键>/source-vocals.wav（没有就用 source.wav），
产出 02-asr/<源键>.words.json：{"text", "words":[{"start","end","word"}], "segments":[...]}
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, NORMALIZED, SOURCE_KEYS, write_json  # noqa: E402

PROMPT = "以下は日本語の音声です。日本語で書き起こしてください。"


def load_16k(path: Path) -> "object":
    """整轨 -> 16k mono float32（faster-whisper 直接吃数组，绕开 av 的接口不兼容）。"""
    import subprocess
    import wave

    import numpy as np

    from common import FFMPEG

    tmp = NORMALIZED / "_words16k.wav"
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(path), "-ac", "1",
                    "-ar", "16000", "-c:a", "pcm_s16le", str(tmp)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdin=subprocess.DEVNULL, check=True)
    with wave.open(str(tmp), "rb") as fh:
        raw = fh.readframes(fh.getnframes())
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def run_one(key: str) -> dict:
    vocals = NORMALIZED / key / "source-vocals.wav"
    wav = vocals if vocals.exists() else NORMALIZED / key / "source.wav"
    from faster_whisper import WhisperModel

    started = time.time()
    audio = load_16k(wav)
    model = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)
    segments, info = model.transcribe(
        audio,
        language="ja",
        beam_size=1,
        condition_on_previous_text=False,
        vad_filter=False,
        word_timestamps=True,
        initial_prompt=PROMPT,
    )

    words, segs, texts = [], [], []
    for seg in segments:
        texts.append(seg.text.strip())
        segs.append({"start": round(seg.start, 3), "end": round(seg.end, 3),
                     "text": seg.text.strip()})
        for w in getattr(seg, "words", None) or []:
            words.append({"start": round(w.start, 3), "end": round(w.end, 3),
                          "word": w.word.strip()})

    payload = {
        "sourceKey": key,
        "wav": str(wav),
        "model": "faster-whisper medium int8",
        "duration": round(info.duration, 3),
        "text": "".join(texts),
        "segments": segs,
        "words": words,
    }
    write_json(ASR / f"{key}.words.json", payload)
    return {"key": key, "words": len(words), "segments": len(segs),
            "seconds": round(time.time() - started, 1), "wav": str(wav)}


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    for key in keys:
        s = run_one(key)
        print(f"[{s['key']}] {s['words']} 词 / {s['segments']} 段  {s['seconds']}s  "
              f"（{Path(s['wav']).name}）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
