"""Cut clean Sandrone voice lines out of the extracted soundtrack.

Keeps the longest speech runs (5-14 s) as zero-shot TTS references.
"""
import os
import re
import subprocess

import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "preview", "sandrone-voice.wav")
OUT = os.path.join(ROOT, "tts", "ref")


def speech_runs(path):
    proc = subprocess.run(
        [FF, "-hide_banner", "-nostats", "-i", path,
         "-af", "silencedetect=noise=-32dB:d=0.55", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = (proc.stderr or "") + (proc.stdout or "")
    starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", log)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", log)]
    total = float(re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", log).group(0).split(":")[2].split(",")[0]) or 0
    duration = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", log)
    if m:
        duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    runs = []
    cursor = 0.0
    for i, s in enumerate(starts):
        if s > cursor + 0.2:
            runs.append((cursor, s))
        cursor = ends[i] if i < len(ends) else duration
    if duration and cursor < duration - 0.2:
        runs.append((cursor, duration))
    return runs


def main():
    os.makedirs(OUT, exist_ok=True)
    runs = speech_runs(SRC)
    good = [(a, b) for a, b in runs if 4.5 <= (b - a) <= 14.0]
    good.sort(key=lambda r: r[0] - r[1])
    picked = good[:6]
    print("speech runs:", len(runs), "-> picked", len(picked))
    for i, (a, b) in enumerate(picked, 1):
        dst = os.path.join(OUT, "line%d.wav" % i)
        subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", "%.2f" % a,
                        "-to", "%.2f" % b, "-i", SRC, "-ac", "1", "-ar", "32000",
                        "-c:a", "pcm_s16le", dst], check=True)
        print("line%d  %.2f -> %.2f  (%.1fs)" % (i, a, b, b - a))


if __name__ == "__main__":
    main()
