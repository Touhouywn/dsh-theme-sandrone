"""voicekit 运行时修补（本机必需，放在 PYTHONPATH 最前）。

背景：本机对一个目录 chmod 会被拒，tempfile 创建后都会 chmod；
DSH 更严格的执行器不允许子进程建管道，FunASR 的「ffmpeg 装了吗」
探测会抛 PermissionError。

voicekit 自带的 tools/sitecustomize.py 处理了前两件，
但它把被拒的 subprocess.run 一律替换成 `CompletedProcess(cmd, 0, b"", b"")`：
platform.py 里 `check_output(..., text=True)` 拿到的就是 bytes，
于是 `platform.machine()` 在 TypeError 上崩掉，imageio_ffmpeg 找不到 ffmpeg。

这里做三件事，语义与自带版一致，只是不骗类型：
1. tempfile 不 chmod；
2. os.mkdir 一律 0o777；
3. subprocess.run 被拒时返回与调用方要求同类型的空结果，
   并把 platform.machine/system/release 钉死（这两个答案库只用来判架构，
   不需要真的去问 Windows）。
"""

import os
import platform
import subprocess
import tempfile

tempfile._resetperms = lambda path: None

_orig_mkdir = os.mkdir


def _mkdir_0777(path, mode=0o777, *args, **kwargs):
    return _orig_mkdir(path, 0o777, *args, **kwargs)


os.mkdir = _mkdir_0777

_orig_run = subprocess.run


def _run_tolerant(*args, **kwargs):
    try:
        return _orig_run(*args, **kwargs)
    except PermissionError:
        cmd = args[0] if args else kwargs.get("args")
        wants_text = bool(
            kwargs.get("text") or kwargs.get("universal_newlines") or kwargs.get("encoding")
        )
        empty = "" if wants_text else b""
        return subprocess.CompletedProcess(cmd, 0, empty, empty)


subprocess.run = _run_tolerant

platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE") or "AMD64"
platform.system = lambda: "Windows"
platform.release = lambda: "10"
