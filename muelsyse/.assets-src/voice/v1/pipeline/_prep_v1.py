"""v1 预备：把复制来的 v2 pipeline 改成缪尔赛思「新枝」v1（路径 + 日语）。

对应 ops/README.md §3。幂等：已改过的条目不会重复改，改完逐条打印。
只改这 4 个文件；改完再单独处理 step03_cut 的 fade（见 README §4 冻结参数）。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

EDITS: list[tuple[str, str, str, int]] = [
    # common.py：ROOT + 源键
    (
        "common.py",
        'ROOT = Path(r"E:\\AI-theme\\columbina\\.assets-src\\voice\\v2")',
        'ROOT = Path(r"E:\\AI-theme\\muelsyse\\.assets-src\\voice\\v1")',
        1,
    ),
    (
        "common.py",
        'SOURCE_KEYS = {\n'
        '    "v1-training": ("BV1C5s6zaE3P", "【少女-哥伦比娅】角色训练语音素材"),\n'
        '    "v2-story62": ("BV1wt2jBwE4p", "哥伦比娅6.2剧情纯净语音可拿来跑rvc"),\n'
        '    "v3-fullvoice": ("BV1fQzSBMEbs", "【原神】哥伦比娅全语音（CV：杨梦露）"),\n'
        '}',
        'SOURCE_KEYS = {\n'
        '    "youngbranch": (\n'
        '        "BV17z421U71V",\n'
        '        "【明日方舟·日文语音集·皮肤语音】缪尔赛思：新枝 Muelsyse: YOUNG BRANCH【CV. 田村由加莉】",\n'
        '    ),\n'
        '}',
        1,
    ),
    # step02a2_words.py：日文 + medium
    (
        "step02a2_words.py",
        'PROMPT = "以下是普通话的句子，用简体中文转写。"',
        'PROMPT = "以下は日本語の音声です。日本語で書き起こしてください。"',
        1,
    ),
    (
        "step02a2_words.py",
        'model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)',
        'model = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)',
        1,
    ),
    (
        "step02a2_words.py",
        'language="zh",',
        'language="ja",',
        1,
    ),
    (
        "step02a2_words.py",
        '"model": "faster-whisper small int8",',
        '"model": "faster-whisper medium int8",',
        1,
    ),
    # step04b_crosscheck.py：日文 + medium + 假名正则
    (
        "step04b_crosscheck.py",
        'PROMPT = "以下是普通话的句子，用简体中文转写。"',
        'PROMPT = "以下は日本語の音声です。日本語で書き起こしてください。"',
        1,
    ),
    (
        "step04b_crosscheck.py",
        'KEEP = re.compile(r"[\\u4e00-\\u9fffA-Za-z0-9]")',
        'KEEP = re.compile(r"[\\u3040-\\u30ff\\u4e00-\\u9fffA-Za-z0-9]")',
        1,
    ),
    (
        "step04b_crosscheck.py",
        'model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)',
        'model = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)',
        1,
    ),
    (
        "step04b_crosscheck.py",
        'language="zh",',
        'language="ja",',
        1,
    ),
    (
        "step04b_crosscheck.py",
        '"model": "faster-whisper small (int8, cpu)",',
        '"model": "faster-whisper medium (int8, cpu)",',
        1,
    ),
    # step015b_floordrop.py：只判 youngbranch
    (
        "step015b_floordrop.py",
        'KEYS = ["v1-training", "v2-story62", "v3-fullvoice"]',
        'KEYS = ["youngbranch"]',
        1,
    ),
]


def apply(edits) -> int:
    bad = 0
    for name, old, new, expect in edits:
        path = HERE / name
        text = path.read_text(encoding="utf-8")
        got = text.count(old)
        if got == 0 and new in text:
            print(f"[skip] {name}: 已是目标值")
            continue
        if got != expect:
            print(f"[FAIL] {name}: 命中 {got} 次，期望 {expect} 次：{old[:40]!r}")
            bad += 1
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        print(f"[edit] {name}: {old[:36]!r} -> {new[:36]!r}")
    return bad


if __name__ == "__main__":
    raise SystemExit(1 if apply(EDITS) else 0)
