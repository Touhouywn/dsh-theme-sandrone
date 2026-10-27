"""04b 双模型互校：用 faster-whisper small 复听，和 SenseVoice 文本算 asrScore。

素材没有台本，所以 brief §04 里的「asrScore = 0.6*Dice(2-gram) + 0.4*字符包含」
只能拿第二个引擎当参照物——这正是设计稿说的「双模型互校」，也是 skill 里
「SenseVoice 不是权威」的落地方式。

只读 01-slices/<源键>/clips/*.wav 与 02-asr/<源键>.json，产出 02-asr/<源键>.cross.json。
一次加载模型、一个源跑完；--limit N 只跑前 N 段（用来标定速度）。
"""

from __future__ import annotations

import re
import sys
import unicodedata
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, SOURCE_KEYS, SLICES, read_json, write_json  # noqa: E402

KEEP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]")
# 让 whisper 尽量出简体：它默认会把中文写成繁体，两边字体不一致会白扣分
PROMPT = "以下は日本語の音声です。日本語で書き起こしてください。"


def norm(text: str) -> str:
    return "".join(KEEP.findall(unicodedata.normalize("NFKC", text or "")))


def similarity(a: str, b: str) -> tuple[float, float, float]:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0, 0.0, 0.0

    def grams(s: str) -> set[str]:
        return {s[i:i + 2] for i in range(max(1, len(s) - 1))}

    ga, gb = grams(a), grams(b)
    dice = 2 * len(ga & gb) / (len(ga) + len(gb)) if (ga or gb) else 0.0
    contain = len(set(a) & set(b)) / max(1, len(set(a)))
    return 0.6 * dice + 0.4 * contain, dice, contain


def read_pcm(path: Path):
    import numpy as np

    with wave.open(str(path), "rb") as fh:
        if fh.getframerate() != 16000 or fh.getnchannels() != 1:
            raise SystemExit(f"切片不是 16k mono：{path}")
        raw = fh.readframes(fh.getnframes())
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def run_one(key: str, limit: int | None = None) -> dict:
    from faster_whisper import WhisperModel

    asr = read_json(ASR / f"{key}.json")
    clips = SLICES / key / "clips"
    items = asr["items"][: limit] if limit else asr["items"]

    model = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)
    rows, failed = [], []
    for item in items:
        audio = read_pcm(clips / item["file"])
        try:
            segments, _ = model.transcribe(
                audio,
                language="ja",
                beam_size=1,
                condition_on_previous_text=False,
                vad_filter=False,
                without_timestamps=True,
                # 不传 initial_prompt：日语逐片复听时该 prompt 会被部分回显
                # （"日本語で書き起こしてください。"），直接把 guess 污染成提示词。
                # 02a2 的整轨转写仍带 prompt（长音频没有这个问题）。
            )
            guess = "".join(seg.text for seg in segments).strip()
        except Exception as exc:  # noqa: BLE001 - 单段异常不能拖垮整源
            failed.append({"id": item["id"], "error": f"{type(exc).__name__}: {exc}"})
            guess = ""
        score, dice, contain = similarity(item["textClean"], guess)
        rows.append({
            "id": item["id"],
            "duration": item["duration"],
            "sensevoice": item["textClean"],
            "whisper": norm(guess),
            "whisperRaw": guess,
            "asrScore": round(score, 3),
            "dice": round(dice, 3),
            "contain": round(contain, 3),
        })

    out = ASR / (f"{key}.cross-sample.json" if limit else f"{key}.cross.json")
    payload = {
        "sourceKey": key,
        "model": "faster-whisper medium (int8, cpu)",
        "items": rows,
        "failed": failed,
    }
    write_json(out, payload)
    scores = sorted(r["asrScore"] for r in rows)
    p = lambda q: scores[min(len(scores) - 1, int(q * (len(scores) - 1)))] if scores else 0
    return {
        "key": key,
        "n": len(rows),
        "failed": len(failed),
        "p10": round(p(0.10), 3),
        "p50": round(p(0.50), 3),
        "p90": round(p(0.90), 3),
        "below055": sum(1 for r in rows if r["asrScore"] < 0.55),
        "out": str(out),
    }


def main(argv: list[str]) -> int:
    limit = None
    keys = []
    for arg in argv:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
        else:
            keys.append(arg)
    keys = keys or list(SOURCE_KEYS)
    for key in keys:
        s = run_one(key, limit)
        print(f"[{s['key']}] {s['n']} 段  失败 {s['failed']}  "
              f"score p10/p50/p90 = {s['p10']}/{s['p50']}/{s['p90']}  "
              f"<0.55 共 {s['below055']}  -> {s['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
