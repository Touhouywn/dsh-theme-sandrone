"""v2 流水线公共件：路径常量、ffmpeg 调用、时长/峰值探测。

约定：
- 所有子进程的 stdout/stderr 一律重定向到文件，不用管道。
- 本模块不读任何中间状态，只提供纯函数。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

# ---- 写死的环境（见 pipeline-brief-for-flash.md §1） ----
PYTHON = r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
FFMPEG = (
    r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python"
    r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)
VOICEKIT_HOME = Path(r"C:\Users\yuanshuifehe\.dsh\voicekit")
VOICEKIT_PY = VOICEKIT_HOME / "venv" / "Scripts" / "python.exe"
VOICEKIT_ENTRY = VOICEKIT_HOME / "tools" / "voicepipe.py"
SHIM = Path(__file__).resolve().parent / "_shim"
NODE = r"C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe"
PLUGIN = Path(r"E:\AI-theme\columbina\dsh-plugin-columbina-voice")

ROOT = Path(r"E:\AI-theme\muelsyse\.assets-src\voice\v1")
SOURCES = ROOT / "sources"
NORMALIZED = ROOT / "00-normalized"
SLICES = ROOT / "01-slices"
ASR = ROOT / "02-asr"
TAGGED = ROOT / "03-tagged"
LOGS = ROOT / "logs"

# 三个素材源：目录键 -> (BV 号, 标题)
SOURCE_KEYS = {
    "youngbranch": (
        "BV17z421U71V",
        "【明日方舟·日文语音集·皮肤语音】缪尔赛思：新枝 Muelsyse: YOUNG BRANCH【CV. 田村由加莉】",
    ),
}


def hashed(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_to_log(cmd: list[str], log_path: Path) -> int:
    """跑一条命令，输出写日志文件（不用管道）。返回退出码。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
        return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode


def probe(path: Path, log_path: Path) -> dict:
    """用 ffmpeg -i 的 stderr 拿时长/编码/采样率/声道，不依赖 ffprobe。"""
    _run_to_log([FFMPEG, "-hide_banner", "-i", str(path)], log_path)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    out = {"duration": None, "codec": "待标", "sampleRate": "待标", "channels": "待标"}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        hh, mm, ss = m.groups()
        out["duration"] = round(int(hh) * 3600 + int(mm) * 60 + float(ss), 3)
    m = re.search(r"Audio:\s*([a-z0-9_]+)[^\n]*?, (\d+) Hz, (mono|stereo|(\d+) channels)", text)
    if m:
        out["codec"] = m.group(1)
        out["sampleRate"] = int(m.group(2))
        out["channels"] = m.group(3) if not m.group(4) else int(m.group(4))
    return out


def max_volume(path: Path, log_path: Path) -> float | None:
    """volumedetect 的最大音量（dBFS）。"""
    _run_to_log(
        [FFMPEG, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        log_path,
    )
    text = log_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", text)
    return float(m.group(1)) if m else None


def voicekit_env() -> dict:
    """voicekit 需要的环境。

    不用 voicekit.cmd：它把 PYTHONPATH 固定成 tools/，会加载自带的
    sitecustomize（那份会在 platform 上崩，见 _shim/sitecustomize.py 的注释）。
    这里把 _shim 放最前，用同一个 venv、同一份模型，只换修补件。
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SHIM)
    env["MODELSCOPE_CACHE"] = str(VOICEKIT_HOME / "models")
    env["HF_HOME"] = str(VOICEKIT_HOME / "hf")
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("VOICEKIT_WORK", str(Path(tempfile.gettempdir()) / "voicekit"))
    env.pop("PYTHONHOME", None)
    return env


def voicekit(args: list[str], log_path: Path) -> int:
    """调 voicekit 子命令。输出写日志，不经管道。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
        return subprocess.run(
            [str(VOICEKIT_PY), str(VOICEKIT_ENTRY), *args],
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=voicekit_env(),
        ).returncode


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
