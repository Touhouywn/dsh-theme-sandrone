"""01.5 人声分离（独立步骤，可单独重跑）。

输入 00-normalized/<源键>/source.wav（48k mono）
输出 00-normalized/<源键>/source-vocals.wav（48k mono）
     v2/01-separate/floor-drop.json（整轨 P5 帧 RMS 前后差）

原轨保留不动。中间文件放 v2/01-separate/<源键>/。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import FFMPEG, NORMALIZED, ROOT, SOURCE_KEYS, _run_to_log  # noqa: E402

RUNTIME_PY = str(Path(r"E:\AI-theme\columbina\.runtime\python310\python.exe"))
# ~/.cache 在这个沙箱里不可写，权重放工作区
TORCH_HOME = Path(r"E:\AI-theme\columbina\.runtime\torch")
PROXY = "http://127.0.0.1:7892"
SEPARATE = ROOT / "01-separate"
LOGS = ROOT / "logs" / "_separate"
SR = 48000
FRAME_MS = 20


def p5_frame_db(wav: Path, tag: str) -> float:
    """整轨 20ms 帧 RMS 的第 5 百分位（dB）。"""
    import numpy as np

    LOGS.mkdir(parents=True, exist_ok=True)
    pcm = LOGS / f"{tag}.pcm"
    code = _run_to_log(
        [FFMPEG, "-v", "error", "-nostdin", "-i", str(wav),
         "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
        pcm.with_suffix(".log"),
    )
    # _run_to_log 只写日志，真正的 PCM 用文件重定向再跑一次
    with open(pcm, "wb") as fh:
        proc = subprocess.run(
            [FFMPEG, "-v", "error", "-nostdin", "-i", str(wav),
             "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
            stdout=fh, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        )
    if proc.returncode != 0:
        raise SystemExit(f"解码失败：{wav}")
    x = np.frombuffer(pcm.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0
    hop = SR * FRAME_MS // 1000
    n = x.size // hop
    frames = x[:n * hop].reshape(n, hop)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    return round(float(20 * np.log10(np.percentile(rms, 5) + 1e-9)), 2)


def separate_one(key: str) -> dict:
    work = SEPARATE / key
    work.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    source = NORMALIZED / key / "source.wav"
    vocals_out = NORMALIZED / key / "source-vocals.wav"
    if not source.exists():
        raise SystemExit(f"缺源：{source}")

    stereo = work / "input-stereo.wav"
    _run_to_log([FFMPEG, "-y", "-v", "error", "-i", str(source), "-ac", "2",
                 "-ar", str(SR), "-c:a", "pcm_s24le", str(stereo)], LOGS / f"{key}-stereo.log")

    outdir = work / "demucs"
    ok = False
    TORCH_HOME.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TORCH_HOME", str(TORCH_HOME))
    os.environ.setdefault("HTTPS_PROXY", PROXY)
    os.environ.setdefault("HTTP_PROXY", PROXY)
    device, started = "cpu", time.time()
    for device in ("cuda", "cpu"):
        log = LOGS / f"{key}-demucs-{device}.log"
        started = time.time()
        code = _run_to_log(
            [RUNTIME_PY, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs",
             "-d", device, "-o", str(outdir), str(stereo)],
            log,
        )
        took = round(time.time() - started, 1)
        if code == 0:
            ok = True
            break
        print(f"  [{key}] demucs -d {device} 失败（{took}s，code {code}），看 {log}")

    if not ok:
        raise SystemExit(f"[{key}] demucs 两种设备都失败")

    stem = outdir / "htdemucs" / "input-stereo" / "vocals.wav"
    if not stem.exists():
        raise SystemExit(f"[{key}] 没找到 vocals：{stem}")

    _run_to_log([FFMPEG, "-y", "-v", "error", "-i", str(stem), "-ac", "1",
                 "-ar", str(SR), "-c:a", "pcm_s24le", str(vocals_out)],
                LOGS / f"{key}-downmix.log")

    before = p5_frame_db(source, f"{key}-before")
    after = p5_frame_db(vocals_out, f"{key}-after")
    return {
        "sourceKey": key,
        "device": device,
        "seconds": round(time.time() - started, 0),
        "source": str(source),
        "vocals": str(vocals_out),
        "p5BeforeDb": before,
        "p5AfterDb": after,
        "dropDb": round(before - after, 2),
    }


def main(argv: list[str]) -> int:
    keys = argv or list(SOURCE_KEYS)
    report_path = SEPARATE / "floor-drop.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    items = report.get("items", {})
    for key in keys:
        print(f"[{key}] 分离中…", flush=True)
        info = separate_one(key)
        items[key] = info
        print(f"[{key}] P5 {info['p5BeforeDb']} → {info['p5AfterDb']} dB（差 {info['dropDb']}）"
              f"，{info['seconds']}s，device={info['device']}", flush=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"frameMs": FRAME_MS, "items": items},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写了 {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
