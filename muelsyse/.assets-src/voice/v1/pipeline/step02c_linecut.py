"""02c linecut：把 VAD 碎片重新归并成「一行台词一个切片」。

为什么需要这一步：本片的 38 行是连续朗读，行内停顿 0.3–1.2s，fsmn-vad 的
min_silence 抓不住行边界，02b 切出 204 个 1.7s 左右的碎片；而骨架是 38 行
整句，单碎片 Dice 到不了门槛。这里用 whisper 整轨词级时间戳做一次全局
字符对齐（semi-global Needleman–Wunsch），把每行 ja_text 映射回词区间，
再按行切整句切片。

音源可选（ops/08）：
  --track=original  source-16k.wav（默认）
  --track=vocals    source-vocals-16k.wav（BGM 例外重跑）

行 21/22 的窗口覆盖（PRO-VERDICT §1 / ops/08 步骤 3）：行 21「なぁに？」在
whisper 里是 な(358.54–358.76) / あ(358.76–358.86) / に?(358.86–359.10)，两路
ASR 都只出子串碎片，字符对齐把行 21 判成 missing、把尾巴「に」并进了行 22。
这里按词帽（首词 start−40ms、末词 end+60ms）钉死行 21 = [358.50, 359.16]，
并把行 22 起点推到下一词 359.98，确保两条切片不重叠。

只读：skeleton-38.tsv、02-asr/<key>.words.json
产出：01-slices/<key>/{linecut.tsv, clips/…} 与 02-asr/<key>.linecut.json
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, NORMALIZED, ROOT, SLICES, read_json, write_json  # noqa: E402
from norm_ja import norm  # noqa: E402
from common import FFMPEG, _run_to_log  # noqa: E402

SKELETON = ROOT / "skeleton-38.tsv"
HEAD_MS = 80
TAIL_MS = 120
FADE_IN_MS = 25
FADE_OUT_MS = 40
MIN_COVER = 0.45       # 行内至少 45% 的参考字能落到 whisper 文本上
MAX_WORDS = 160        # 一行的词数上限（防串到别的行）
WORD_CAP_MIN = 80      # 相邻整句切片的最小间隔（词帽口径）

# 行 21/22 的手工窗口（ms）。None = 沿用字符对齐算出来的那端。
SPAN_OVERRIDES: dict[str, tuple[int | None, int | None]] = {
    "21": (358540, 359100),
    "22": (359980, None),
}


def load_ref() -> tuple[str, list[dict]]:
    rows = list(csv.DictReader(open(SKELETON, encoding="utf-8"), delimiter="\t"))
    ref, spans = "", []
    for r in rows:
        t = norm(r["ja_text"])
        spans.append({"prts_idx": r["prts_idx"], "key": r["key"],
                      "ref_start": len(ref), "ref_end": len(ref) + len(t), "ref": t})
        ref += t
    return ref, spans


def load_hyp(key: str) -> tuple[str, list[dict], list[int]]:
    words = read_json(ASR / f"{key}.words.json")["words"]
    chars, wmap, kept = [], [], []
    for wi, w in enumerate(words):
        t = norm(w["word"])
        if not t:
            continue
        kept.append(w)
        chars.append(t)
        wmap.extend([len(kept) - 1] * len(t))
    return "".join(chars), kept, wmap


def align(ref: str, hyp: str) -> list[int | None]:
    """semi-global NW（hyp 两端可自由跳过），返回每个 ref 字对齐到的 hyp 下标。"""
    m, n = len(ref), len(hyp)
    MATCH, MIS, GAP = 2, -1, -1
    prev = [0] * (n + 1)            # dp[0][*] = 0（hyp 前缀自由）
    back: list[list[int]] = []
    # back 每格存：0=对角(匹配/错配) 1=上(跳 hyp) 2=左(跳 ref)
    for i in range(1, m + 1):
        cur = [GAP * i] + [0] * n   # dp[i][0]：ref 前缀全 gap，但不设 0（内部用）
        b = [2] * (n + 1)
        for j in range(1, n + 1):
            diag = prev[j - 1] + (MATCH if ref[i - 1] == hyp[j - 1] else MIS)
            up = prev[j] + GAP       # 跳过 hyp 字
            left = cur[j - 1] + GAP  # 跳过 ref 字（gap）
            best, how = diag, 0
            if up > best:
                best, how = up, 1
            if left > best:
                best, how = left, 2
            cur[j], b[j] = best, how
        back.append(b)
        prev = cur
    # 末尾：ref 必须全消费，hyp 可在尾部自由
    j_end = max(range(n + 1), key=lambda j: prev[j])
    out: list[int | None] = [None] * m
    i, j = m, j_end
    while i > 0 and j > 0:
        how = back[i - 1][j]
        if how == 0:
            out[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif how == 1:   # 上：ref 这一字没有对应（hyp 用 gap 跳过）
            i -= 1
        else:            # 左：hyp 这一字被跳过
            j -= 1
    return out


def cut_one(wav: Path, start_ms: int, end_ms: int, target: Path, log: Path) -> dict:
    import wave

    with wave.open(str(wav), "rb") as fh:
        total = fh.getnframes() / fh.getframerate() * 1000
    s = max(0, start_ms - HEAD_MS)
    e = min(total, end_ms + TAIL_MS)
    dur = (e - s) / 1000
    fade_out = max(0.0, dur - FADE_OUT_MS / 1000)
    code = _run_to_log([
        FFMPEG, "-y", "-v", "error", "-ss", f"{s/1000:.3f}", "-i", str(wav),
        "-t", f"{dur:.3f}",
        "-af", (f"afade=t=in:st=0:d={FADE_IN_MS/1000},"
                f"afade=t=out:st={fade_out:.3f}:d={FADE_OUT_MS/1000}"),
        "-c:a", "pcm_s16le", str(target),
    ], log)
    if code != 0:
        raise SystemExit(f"切失败：{target.name}")
    return {"sourceStart": s, "sourceEnd": e, "duration": round(dur, 3)}


def main(argv: list[str]) -> int:
    key, track = "youngbranch", "original"
    for arg in argv:
        if arg.startswith("--track="):
            track = arg.split("=", 1)[1]
        else:
            key = arg
    if track not in ("original", "vocals"):
        raise SystemExit(f"未知 track：{track}")
    wav = NORMALIZED / key / ("source-vocals-16k.wav" if track == "vocals"
                              else "source-16k.wav")
    if not wav.exists():
        raise SystemExit(f"缺音源：{wav}")

    ref, spans = load_ref()
    hyp, words, wmap = load_hyp(key)
    print(f"[{key}] track={track}  ref {len(ref)} 字 / hyp {len(hyp)} 字 / {len(words)} 词")
    mapping = align(ref, hyp)

    outdir = SLICES / key
    clips = outdir / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    for old in clips.glob("*.wav"):
        old.unlink()
    for old in clips.glob("index.json"):
        old.unlink()

    log = ROOT / "logs" / key / "02c-linecut.log"
    plan, missing = [], []
    for span in spans:
        idx = span["prts_idx"]
        got = [q for q in mapping[span["ref_start"]:span["ref_end"]] if q is not None]
        ref_len = span["ref_end"] - span["ref_start"]
        cover = len(got) / ref_len if ref_len else 0.0
        start_ms = end_ms = None
        if got and cover >= MIN_COVER:
            w0, w1 = wmap[min(got)], wmap[max(got)]
            if w1 - w0 + 1 <= MAX_WORDS:
                start_ms = int(round(words[w0]["start"] * 1000))
                end_ms = int(round(words[w1]["end"] * 1000))
        if idx in SPAN_OVERRIDES:
            o_start, o_end = SPAN_OVERRIDES[idx]
            start_ms = o_start if o_start is not None else start_ms
            end_ms = o_end if o_end is not None else end_ms
        if start_ms is None or end_ms is None or end_ms <= start_ms:
            missing.append({**{k: v for k, v in span.items() if k != "ref"},
                            "coverage": round(cover, 3)})
            continue
        plan.append({"prts_idx": idx, "key": span["key"], "start": start_ms,
                     "end": end_ms, "coverage": round(cover, 3)})

    # 相邻切片不重叠：起点至少是上一行末尾 + 80ms，落不到词边界就顺延到下一个词
    plan.sort(key=lambda p: p["start"])
    for prev, cur in zip(plan, plan[1:]):
        need = prev["end"] + WORD_CAP_MIN
        if cur["start"] < need:
            later = [w["start"] * 1000 for w in words if w["start"] * 1000 >= need]
            if later:
                cur["start"] = int(min(later))

    index = []
    for p in plan:
        cid = f"c{int(p['prts_idx']):04d}"
        info = cut_one(wav, p["start"], p["end"], clips / f"{cid}.wav", log)
        index.append({"id": cid, "file": f"{cid}.wav", **info})
        print(f"  row {p['prts_idx']:>2} {p['key']:<8} {p['start']:>6}-{p['end']:>6}ms "
              f"cover {p['coverage']:.2f}")

    write_json(clips / "index.json", {"sourceKey": key, "clips": index,
                                      "method": "linecut-wordspan", "track": track})
    write_json(ASR / f"{key}.linecut.json",
               {"sourceKey": key, "track": track, "wav": str(wav),
                "rows": plan, "missing": missing,
                "refChars": len(ref), "hypChars": len(hyp)})
    print(f"行切片 {len(plan)}，缺 {len(missing)}：{[m['prts_idx'] for m in missing]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
