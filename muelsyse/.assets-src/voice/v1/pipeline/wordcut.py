"""词边界精修：02b 与 06 必须调用同一套「第一个词 / 最后一个词」定义。

修正稿口径：
  last_word  = { word.start >= S-120ms 且 word.end <= energy_end } 里 end 最大者
  clip_end   = min(energy_end + 40ms, last_word.end + 60ms)
  first_word = { word.end <= E+120ms 且 word.start >= energy_start } 里 start 最小者
  clip_start = max(energy_start - 50ms, first_word.start - 40ms)

切边和复核都 import 这里，不各写一份。
"""

from __future__ import annotations

SLACK_MS = 120
HEAD_PAD_MS = 50
TAIL_PAD_MS = 40
WORD_HEAD_PAD_MS = 40
WORD_TAIL_PAD_MS = 60


def last_word_end(words: list[dict], energy_start_ms: float,
                  energy_end_ms: float) -> float | None:
    """落在 [S-120, energy_end] 里的最后一个词的 end（毫秒）。

    whisper 偶尔给出跨很长一段的「词」（实测「再見」跨了 1.7s），
    所以用「起点在能量范围内」判断，不再要求 end <= energy_end。
    """
    best = None
    for w in words:
        start = w["start"] * 1000
        end = w["end"] * 1000
        if start >= energy_start_ms - SLACK_MS and start < energy_end_ms:
            if best is None or end > best:
                best = end
    return best


def first_word_start(words: list[dict], energy_start_ms: float,
                     energy_end_ms: float) -> float | None:
    """落在 [energy_start, E+120] 里的第一个词的 start（毫秒）。

    同样放宽：只要这个词的尾巴越过能量起点，就算这一句的第一个词——
    否则「再見」这种长跨度词会被漏掉，头就会切掉首字。
    """
    best = None
    for w in words:
        start = w["start"] * 1000
        end = w["end"] * 1000
        if end > energy_start_ms and start < energy_end_ms + SLACK_MS:
            if best is None or start < best:
                best = start
    return best


def clip_bounds(words: list[dict], energy_start_ms: float,
                energy_end_ms: float) -> dict:
    """返回 {start, end, lastWordEnd, firstWordStart, fromWord}。"""
    lw = last_word_end(words, energy_start_ms, energy_end_ms)
    fw = first_word_start(words, energy_start_ms, energy_end_ms)
    end = energy_end_ms + TAIL_PAD_MS if lw is None else min(energy_end_ms + TAIL_PAD_MS,
                                                             lw + WORD_TAIL_PAD_MS)
    start = energy_start_ms - HEAD_PAD_MS if fw is None else max(energy_start_ms - HEAD_PAD_MS,
                                                                 fw - WORD_HEAD_PAD_MS)
    return {"start": start, "end": end, "lastWordEnd": lw, "firstWordStart": fw,
            "fromWord": lw is not None and fw is not None}


def overrun_ms(clip_end_ms: float, energy_end_ms: float, words: list[dict],
               energy_start_ms: float) -> float | None:
    """06 复核用：E − (last_word.end + 60ms)。没有词返回 None。"""
    lw = last_word_end(words, energy_start_ms, energy_end_ms)
    if lw is None:
        return None
    return clip_end_ms - (lw + WORD_TAIL_PAD_MS)
