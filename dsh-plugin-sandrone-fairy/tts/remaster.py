"""Raise the volume of already-baked clips without re-synthesising them.

GPU 正被训练占着，重新合成会卡住；这里直接对现有 m4a 做一次增益+限幅重建。
"""

import os
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.path.join(BASE, "assets", "voice")
FFMPEG = r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe"
FILTER = os.environ.get("SANDRONE_TTS_FILTER", "loudnorm=I=-14:TP=-1.5:LRA=11")


def probe_peak(path):
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, errors="ignore",
    )
    for line in result.stderr.splitlines():
        if "max_volume" in line or "mean_volume" in line:
            yield line.strip()


def main():
    files = sorted(name for name in os.listdir(VOICE) if name.endswith(".m4a"))
    print("%d clips, filter=%s" % (len(files), FILTER))
    for name in files:
        src = os.path.join(VOICE, name)
        tmp = src + ".tmp.m4a"
        proc = subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-i", src,
             "-af", FILTER, "-c:a", "aac", "-b:a", "128k", tmp],
            capture_output=True, text=True, errors="ignore",
        )
        if proc.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) < 2048:
            print("  FAIL %s %s" % (name, proc.stderr.strip()[:120]))
            if os.path.exists(tmp):
                os.remove(tmp)
            continue
        os.replace(tmp, src)
        before = os.path.getsize(src)
        print("  ok %-18s %6dKB" % (name, before // 1024))

    print("--- levels after remaster ---")
    for name in files[:3]:
        for line in probe_peak(os.path.join(VOICE, name)):
            print(" ", name, line)


if __name__ == "__main__":
    main()
