"""把 28 条预制台词拼成一条试听音频，并生成一个点击即播的清单页。

用法: python tools/voice_sheet.py
产物: preview/voice-all.m4a、preview/voice-sheet.html
"""

import html
import imageio_ffmpeg
import io
import json
import os
import subprocess
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.path.join(ROOT, "assets", "voice")
PREVIEW = os.path.join(ROOT, "preview")
TMP = os.path.join(PREVIEW, "tmp-voice")
FFMPEG = os.environ.get(
    "SANDRONE_FFMPEG",
    imageio_ffmpeg.get_ffmpeg_exe(),
)

GROUPS = [
    ("开屏", ["welcome", "welcome-back"]),
    ("问候", ["greet-morning", "greet-noon", "greet-afternoon", "greet-evening", "greet-night"]),
    ("低语", ["whisper-listen", "whisper-gear", "whisper-idle", "whisper-rest", "whisper-water"]),
    ("反应 · 情绪", ["react-hello", "react-thanks", "react-praise", "react-flatter", "react-tease",
                     "react-tired", "react-night", "react-done", "react-error", "react-fail", "react-win",
                     "react-giveup", "react-rest10", "react-busy", "react-agree", "react-curious", "react-sorry"]),
    ("反应 · 场景", ["react-morning", "react-wake", "react-goodnight", "react-overtime", "react-meal",
                     "react-stretch", "react-sick", "react-comfort", "react-nightlight", "react-wrapup"]),
    ("时段", ["idle-dawn", "idle-noon", "idle-afternoon", "idle-dusk", "idle-late", "idle-long"]),
    ("其他", ["thinking", "voice-demo", "farewell"]),
]


def run(args):
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.decode("utf-8", "replace")[-800:])
    return proc.stdout


def to_wav(src, dst):
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-ar", "32000", "-ac", "1", "-c:a", "pcm_s16le", dst])


def make_silence(dst, seconds=0.9, rate=32000):
    frames = int(seconds * rate)
    with wave.open(dst, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x00\x00" * frames)


def duration_of(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def main():
    pack = json.loads(io.open(os.path.join(ROOT, "tts", "pack.json"), encoding="utf-8").read())
    os.makedirs(TMP, exist_ok=True)
    silence = os.path.join(TMP, "_sil.wav")
    make_silence(silence)

    order = [key for _, keys in GROUPS for key in keys]
    parts, total = [], 0.0
    for key in order:
        src = os.path.join(VOICE, key + ".m4a")
        if not os.path.exists(src):
            print("skip missing", key)
            continue
        wav = os.path.join(TMP, key + ".wav")
        to_wav(src, wav)
        total += duration_of(wav)
        parts.append(wav)
        parts.append(silence)

    listing = os.path.join(TMP, "list.txt")
    with io.open(listing, "w", encoding="utf-8", newline="\n") as fh:
        for part in parts:
            fh.write("file '%s'\n" % part.replace("\\", "/"))

    out = os.path.join(PREVIEW, "voice-all.m4a")
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listing, "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out])

    cards = []
    n = 0
    for name, keys in GROUPS:
        rows = []
        for key in keys:
            if key not in pack:
                continue
            n += 1
            text = html.escape(str(pack[key]))
            rows.append(
                '<div class="row"><span class="idx">%02d</span>'
                '<div class="body"><div class="key">%s</div><div class="text">%s</div></div>'
                '<audio controls preload="none" src="../assets/voice/%s.m4a"></audio></div>'
                % (n, html.escape(key), text, key)
            )
        cards.append('<section><h2>%s</h2>%s</section>' % (html.escape(name), "".join(rows)))

    page = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>桑多涅 · 全部预制台词</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; padding:28px 32px 60px; background:#07081a; color:#e8e3ff;
         font:15px/1.6 "Microsoft YaHei", system-ui, sans-serif; }
  h1 { font-size:22px; letter-spacing:.16em; margin:0 0 4px; }
  .sub { color:#a49bd4; font-size:13px; margin-bottom:22px; }
  h2 { font-size:14px; letter-spacing:.24em; color:#c7a6ff; margin:26px 0 10px;
       border-left:3px solid #a878ff; padding-left:10px; }
  .row { display:flex; align-items:center; gap:14px; padding:9px 12px; border-radius:10px; }
  .row:hover { background:rgba(126,96,226,.12); }
  .idx { width:26px; color:#6f68a0; font-variant-numeric:tabular-nums; font-size:13px; }
  .body { flex:1; min-width:0; }
  .key { font-size:12px; color:#8f88bd; letter-spacing:.08em; }
  .text { font-size:15px; }
  audio { width:210px; height:32px; }
  .hint { margin-top:26px; color:#6f68a0; font-size:12px; }
  a { color:#c7a6ff; }
</style></head><body>
<h1>桑多涅 · 全部预制台词</h1>
<div class="sub">共 %d 条 · 逐条点播；整段连播见 <a href="voice-all.m4a">voice-all.m4a</a>（总长约 %d 分 %02d 秒）</div>
%s
<div class="hint">这些是烘好的固定台词，播放零延迟；聊天里的回复是现场合成的，走同一套参考音。</div>
</body></html>
""" % (n, int((total + 0.9 * n) // 60), int((total + 0.9 * n) % 60), "".join(cards))

    sheet = os.path.join(PREVIEW, "voice-sheet.html")
    io.open(sheet, "w", encoding="utf-8", newline="\n").write(page)
    print("clips:", n, "audio:", os.path.getsize(out) // 1024, "KB", "total:%.1fs" % total)
    print(sheet)


if __name__ == "__main__":
    main()
