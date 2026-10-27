"""v4 链路：人声轨重切 -> 16k 切片 -> SenseVoice 转写 -> 词表互校。

每步只读上一步的产物，可单独重跑：
  wav16   voicekit wav source-vocals.wav -> source-vocals-16k.wav
  vad     voicekit vad -> 01-slices/<key>/vad.json
  rules   step02b_rules_v4 -> segments.json/tsv（词边界 + 能量谷）
  cut     16k 切片，边界已是最终值，不再加留白；淡入 25 / 淡出 40
  asr     voicekit asr -> 02-asr/<key>.json
  cross   用整轨词时间戳拼出每段的 whisper 文本 -> 02-asr/<key>.cross.json

用法：python chain_v4.py [wav16|vad|rules|cut|asr|cross|all] [源键 ...]
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import step02b_rules_v4 as rules  # noqa: E402
from common import (  # noqa: E402
    ASR,
    FFMPEG,
    NORMALIZED,
    SLICES,
    SOURCE_KEYS,
    _run_to_log,
    read_json,
    voicekit,
    write_json,
)

FADE_IN_MS = rules.RULES["fadeInMs"]
FADE_OUT_MS = rules.RULES["fadeOutMs"]
LOGS = Path(__file__).resolve().parent.parent / "logs"


def vocals_16k(key: str) -> Path:
    return NORMALIZED / key / "source-vocals-16k.wav"


def step_wav16(key: str) -> None:
    src = NORMALIZED / key / "source-vocals.wav"
    if not src.exists():
        raise SystemExit(f"缺 {src}")
    code = voicekit(["wav", str(src), str(vocals_16k(key))], LOGS / key / "v4-wav16.log")
    if code != 0:
        raise SystemExit("voicekit wav 失败")


def step_vad(key: str) -> None:
    out = SLICES / key / "vad.json"
    code = voicekit(["vad", str(vocals_16k(key)), str(out)], LOGS / key / "v4-vad.log")
    if code != 0:
        raise SystemExit("voicekit vad 失败")
    print(f"[{key}] vad {len(read_json(out)['segments'])} 段", flush=True)


def step_rules(key: str) -> None:
    s = rules.run_one(key)
    print(f"[{key}] rules kept {s['kept']}（reject {s['rejected']}）{s['speech']}s  "
          f"词头 {s['headFromWord']} / 词尾 {s['tailFromWord']} / 谷退 {s['valleyFallback']}",
          flush=True)


def step_cut(key: str) -> None:
    segs = read_json(SLICES / key / "segments.json")["segments"]
    wav = vocals_16k(key)
    with wave.open(str(wav), "rb") as fh:
        total_ms = fh.getnframes() / fh.getframerate() * 1000
    clips = SLICES / key / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    for old in clips.glob("*.wav"):
        old.unlink()

    index = []
    for n, seg in enumerate(segs, start=1):
        start = max(0.0, seg["start"])
        end = min(total_ms, seg["end"])
        dur = (end - start) / 1000
        if dur <= 0.05:
            continue
        name = f"c{n:04d}.wav"
        fade_out = max(0.0, dur - FADE_OUT_MS / 1000)
        code = _run_to_log([
            FFMPEG, "-y", "-v", "error",
            "-ss", f"{start / 1000:.3f}", "-i", str(wav), "-t", f"{dur:.3f}",
            "-af", (f"afade=t=in:st=0:d={FADE_IN_MS / 1000},"
                    f"afade=t=out:st={fade_out:.3f}:d={FADE_OUT_MS / 1000}"),
            "-c:a", "pcm_s16le", str(clips / name),
        ], LOGS / key / "v4-cut.log")
        if code != 0:
            raise SystemExit(f"[{key}] 切 {name} 失败")
        index.append({"id": f"c{n:04d}", "file": name,
                      "sourceStart": int(start), "sourceEnd": int(end),
                      "energyStart": int(seg.get("energyStart", start)),
                      "energyEnd": int(seg.get("energyEnd", end)),
                      "duration": round(dur, 3)})
    write_json(clips / "index.json", {"sourceKey": key, "clips": index})
    print(f"[{key}] cut {len(index)} 片", flush=True)


def step_asr(key: str) -> None:
    clips = SLICES / key / "clips"
    out = ASR / f"{key}.json"
    code = voicekit(["asr", str(clips), str(out)], LOGS / key / "v4-asr.log")
    if code != 0:
        raise SystemExit("voicekit asr 失败")
    print(f"[{key}] asr {len(read_json(out)['items'])} 条", flush=True)


def step_cross(key: str) -> None:
    """用整轨词时间戳拼每段的 whisper 文本，算 asrScore（6:4 Dice/包含）。"""
    import re
    import unicodedata

    def norm(text: str) -> str:
        return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", unicodedata.normalize("NFKC", text or "")))

    # whisper 整轨经常吐繁体（initial_prompt 只对开头几个窗口有效），
    # 和简体的 SenseVoice 比对会白扣分，先转简体再算。
    sys.path.insert(0, str(Path(r"E:\AI-theme\columbina\.assets-src\voice\v2\pylib")))
    try:
        import zhconv

        def t2s(text: str) -> str:
            return zhconv.convert(text or "", "zh-cn")
    except Exception:  # noqa: BLE001 - 没装就直通
        def t2s(text: str) -> str:
            return text

    def sim(a: str, b: str) -> tuple[float, float, float]:
        a, b = norm(a), norm(b)
        if not a or not b:
            return 0.0, 0.0, 0.0

        def grams(s):
            return {s[i:i + 2] for i in range(max(1, len(s) - 1))}

        ga, gb = grams(a), grams(b)
        dice = 2 * len(ga & gb) / (len(ga) + len(gb)) if (ga or gb) else 0.0
        contain = len(set(a) & set(b)) / max(1, len(set(a)))
        return 0.6 * dice + 0.4 * contain, dice, contain

    words = read_json(ASR / f"{key}.words.json")["words"]
    items = read_json(ASR / f"{key}.json")["items"]
    index = {c["file"]: c for c in read_json(SLICES / key / "clips" / "index.json")["clips"]}
    rows, empty = [], 0
    for row in items:
        clip = index[row["file"]]
        s, e = clip["sourceStart"], clip["sourceEnd"]
        # 只要词与该段有重叠就算：whisper 的「词」常常比短段还长，
        # 半长/中点这类规则会把整段判成没词。
        guess = "".join(w["word"] for w in words
                        if w["end"] * 1000 >= s and w["start"] * 1000 <= e)
        guess = t2s(guess)
        sv = norm(re.sub(r"<\|[^|]*\|>", "", row["text"]))
        score, dice, contain = sim(sv, guess)
        if not guess:
            empty += 1
        rows.append({"id": clip["id"], "duration": clip["duration"],
                     "sensevoice": sv, "whisper": norm(guess), "whisperRaw": guess,
                     "asrScore": round(score, 3), "dice": round(dice, 3),
                     "contain": round(contain, 3),
                     "wordStart": s, "wordEnd": e})
    write_json(ASR / f"{key}.cross.json", {"sourceKey": key,
                                           "model": "full-track whisper words",
                                           "items": rows, "emptyGuess": empty})
    print(f"[{key}] cross {len(rows)} 条，空 {empty}", flush=True)


STEPS = {"wav16": step_wav16, "vad": step_vad, "rules": step_rules,
         "cut": step_cut, "asr": step_asr, "cross": step_cross}


def main(argv: list[str]) -> int:
    chosen = [a for a in argv if a in STEPS]
    if "all" in argv or not chosen:
        order = list(STEPS)
    else:
        order = [name for name in STEPS if name in chosen]
    keys = [a for a in argv if a in SOURCE_KEYS] or list(SOURCE_KEYS)
    for key in keys:
        for name in order:
            STEPS[name](key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
