"""Build the opening score: CC-BY bed + synthesized mechanical SFX.

Usage:
  python tools/build-opening-media.py --bgm "Impact Moderato.mp3" --out assets/opening-score.m4a

The script is deterministic: it always renders the same 16.6 s cue, so a
rebuilt score matches the storyboard timings in lib/client.js.
"""
import argparse
import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
DURATION = 16.6
BGM_OFFSET = 2.4
BGM_GAIN = 0.62


def read_wav(path):
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        rate = handle.getframerate()
        frames = handle.getnframes()
        data = np.frombuffer(handle.readframes(frames), dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels)
    else:
        data = data.reshape(-1, 1)
    if rate != SR:
        raise SystemExit(f"expected {SR} Hz, got {rate} Hz: resample the bed first")
    return data


def add(buf, start, mono, left_gain=1.0, right_gain=1.0):
    begin = max(0, int(start * SR))
    end = min(buf.shape[0], begin + len(mono))
    if end <= begin:
        return
    part = mono[: end - begin]
    buf[begin:end, 0] += part * left_gain
    buf[begin:end, 1] += part * right_gain


def tvec(seconds):
    return np.arange(int(seconds * SR), dtype=np.float64) / SR


def impact(duration=1.4):
    t = tvec(duration)
    click = np.random.default_rng(7).normal(0, 1, len(t)) * np.exp(-28 * t)
    sub = np.sin(2 * np.pi * (44 * t - 10 * t * t)) * np.exp(-4.2 * t)
    metal = sum(np.sin(2 * np.pi * f * t) * np.exp(-5.5 * t) for f in (173.0, 262.0, 401.0)) / 3
    return (0.85 * sub + 0.35 * click + 0.22 * metal).astype(np.float32)


def whoosh(duration=1.1, reverse=False):
    t = tvec(duration)
    noise = np.random.default_rng(11).normal(0, 1, len(t))
    # crude band-lift: difference removes the low rumble, the envelope shapes it
    noise = np.diff(noise, prepend=noise[0])
    env = np.sin(np.pi * t / duration) ** 2
    if reverse:
        env = env[::-1]
    return (noise * env * 0.42).astype(np.float32)


def riser(duration=2.0):
    t = tvec(duration)
    noise = np.random.default_rng(13).normal(0, 1, len(t))
    noise = np.diff(noise, prepend=noise[0])
    sweep = np.sin(2 * np.pi * (70 * t + 180 * t * t / duration))
    env = (t / duration) ** 2
    return ((0.30 * noise + 0.24 * sweep) * env).astype(np.float32)


def shimmer(duration=2.8):
    t = tvec(duration)
    tones = sum(np.sin(2 * np.pi * f * t) for f in (880.0, 1174.7, 1568.0)) / 3
    env = np.exp(-1.6 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 6 * t))
    return (tones * env * 0.16).astype(np.float32)


def glitch(duration=0.09):
    t = tvec(duration)
    rng = np.random.default_rng(17)
    noise = rng.normal(0, 1, len(t))
    square = np.sign(np.sin(2 * np.pi * 1200 * t))
    return ((noise * 0.35 + square * 0.18) * np.exp(-18 * t)).astype(np.float32)


def tick(duration=0.03):
    t = tvec(duration)
    noise = np.random.default_rng(19).normal(0, 1, len(t))
    return (noise * np.exp(-90 * t) * 0.16).astype(np.float32)


def ffmpeg_exe():
    candidate = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if candidate:
        return candidate
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:  # pragma: no cover - environment dependent
        raise SystemExit("ffmpeg not found: put it on PATH or set FFMPEG") from error


def build(bgm_path, voice_clips, out_path):
    bed = read_wav(bgm_path)
    total = int(DURATION * SR)
    offset = int(BGM_OFFSET * SR)
    segment = np.zeros((total, 2), dtype=np.float32)
    available = min(total, bed.shape[0] - offset)
    segment[:available] = bed[offset : offset + available] * BGM_GAIN

    # Fade the bed in and out; the hits below sit on top of the fades.
    fade_in = int(0.55 * SR)
    fade_out = int(1.6 * SR)
    segment[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    segment[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]

    # Duck the bed under each voice line so the words stay legible.
    duck = np.ones(total, dtype=np.float32)
    voices = []
    for path, at in voice_clips:
        voice = read_wav(path)
        voice_mono = voice.mean(axis=1)
        voice_mono = voice_mono / max(1e-6, float(np.abs(voice_mono).max())) * 0.68
        voices.append((at, voice_mono))
        start = max(0, int((at - 0.10) * SR))
        end = min(total, int((at + len(voice_mono) / SR + 0.18) * SR))
        duck[start:end] = 0.66
    # Smooth the ducking edges so it follows the voice instead of clicking.
    kernel = int(0.08 * SR)
    if kernel > 1:
        duck = np.convolve(duck, np.ones(kernel) / kernel, mode="same")
    segment *= duck[:, None]

    add(segment, 0.05, whoosh(1.4), 0.7, 0.7)
    add(segment, 0.55, impact(1.0) * 0.35, 0.9, 0.8)
    for index, at in enumerate((1.35, 1.85, 2.35, 3.05, 3.95, 5.05, 6.05, 6.95, 8.35)):
        add(segment, at, glitch(), 0.55 + 0.05 * (index % 2), 0.5)
    for at in np.arange(1.2, 8.8, 0.42):
        add(segment, float(at), tick(), 0.45, 0.55)
    add(segment, 7.35, riser(2.25), 0.75, 0.7)
    add(segment, 9.6, impact(1.6), 1.0, 1.0)
    add(segment, 9.6, shimmer(3.2), 0.8, 1.0)
    add(segment, 11.15, impact(0.9) * 0.42, 0.7, 0.8)
    add(segment, 12.7, shimmer(2.2) * 0.6, 0.9, 0.7)
    add(segment, 14.9, whoosh(1.25, reverse=True), 0.8, 0.8)

    for at, voice_mono in voices:
        add(segment, at, voice_mono, 0.95, 0.95)

    mixed = np.tanh(segment * 1.15) / np.tanh(1.15)
    peak = float(np.abs(mixed).max())
    if peak > 0:
        mixed = mixed * (0.70 / peak)
    pcm = (np.clip(mixed, -1, 1) * 32767).astype(np.int16)
    print(f"dynamics: raw peak={peak:.3f} normalized={float(np.abs(mixed).max()):.3f} pcm={int(np.abs(pcm).max())}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp = out_path.with_suffix(".build.wav")
    with wave.open(str(temp), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())

    subprocess.run(
        [
            ffmpeg_exe(),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(temp),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out_path),
        ],
        check=True,
    )
    if os.environ.get("KEEP_BUILD_WAV") == "1":
        print(f"kept {temp}")
    else:
        temp.unlink()
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bgm", required=True, help="16-bit 48 kHz WAV bed (resample the MP3 first)")
    parser.add_argument("--voice-clip", action="append", default=[], metavar="PATH@SECONDS", help="voice line and its start time (repeatable)")
    parser.add_argument("--out", default="assets/opening-score.m4a", help="final .m4a path")
    args = parser.parse_args()
    clips = []
    for spec in args.voice_clip:
        path, at = spec.rsplit("@", 1)
        clips.append((Path(path), float(at)))
    build(Path(args.bgm), clips, Path(args.out))


if __name__ == "__main__":
    main()
