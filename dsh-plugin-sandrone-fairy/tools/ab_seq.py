"""把 ab-fix 的「旧 / 新」两版拼成一条对比音频（先统一解码成 32k 单声道 wav 再拼）。"""

import imageio_ffmpeg
import io
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AB = os.path.join(ROOT, "preview", "ab-fix")
OLD = os.path.join(ROOT, "assets", "voice")
FF = os.environ.get(
    "SANDRONE_FFMPEG",
    imageio_ffmpeg.get_ffmpeg_exe(),
)


def run(args):
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.decode("utf-8", "replace")[-600:])


def to_wav(src, dst):
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-ar", "32000", "-ac", "1", "-c:a", "pcm_s16le", dst])


def main():
    tmp = os.path.join(AB, "_seq")
    os.makedirs(tmp, exist_ok=True)
    sil = os.path.join(tmp, "sil0.7.wav")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "anullsrc=r=32000:cl=mono", "-t", "0.7", sil])

    report = json.loads(io.open(os.path.join(AB, "report.json"), encoding="utf-8").read())
    parts = []
    for row in report:
        key = row["key"]
        for tag, src in (("old", os.path.join(OLD, key + ".m4a")), ("new", os.path.join(AB, key + ".m4a"))):
            wav = os.path.join(tmp, "%s-%s.wav" % (key, tag))
            to_wav(src, wav)
            parts += [wav, sil]
        parts.append(sil)

    listing = os.path.join(tmp, "list.txt")
    with io.open(listing, "w", encoding="utf-8", newline="\n") as fh:
        for part in parts:
            fh.write("file '" + part.replace("\\", "/") + "'\n")

    out = os.path.join(AB, "AB-旧-新-交替.m4a")
    run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listing, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])
    print("ok", os.path.getsize(out) // 1024, "KB")
    for i, row in enumerate(report, 1):
        print("%02d 旧→新  %-18s %-5s  %s" % (i, row["key"], row["pool"], row["text"]))


if __name__ == "__main__":
    main()
