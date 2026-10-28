"""把已烘好的 wav 按官网参数转成 assets/voice/<key>.m4a（掐头/淡入/归一/128k aac）。

用法：
    python tools/apply_clip.py <key> <wav 路径>
"""

import imageio_ffmpeg
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = imageio_ffmpeg.get_ffmpeg_exe()
FILTER = (
    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
    "afade=t=in:st=0:d=0.015,"
    "adelay=60:all=1,"
    "loudnorm=I=-14:TP=-1.5:LRA=11"
)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    key, src = sys.argv[1], sys.argv[2]
    dst = os.path.join(BASE, "assets", "voice", key + ".m4a")
    r = subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-af", FILTER, "-c:a", "aac", "-b:a", "128k", dst],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not os.path.exists(dst):
        print("FAILED:", r.stderr.strip()[-400:])
        return 1
    probe = subprocess.run(
        [FF, "-hide_banner", "-i", dst, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    peak = next((l.split("max_volume:")[1].strip() for l in probe.splitlines() if "max_volume" in l), "?")
    print("%s  %d KB  peak %s" % (key, os.path.getsize(dst) // 1024, peak))
    return 0


if __name__ == "__main__":
    sys.exit(main())
