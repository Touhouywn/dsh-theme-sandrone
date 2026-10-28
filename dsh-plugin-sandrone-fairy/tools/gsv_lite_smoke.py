"""GSV-TTS-Lite 冒烟测试：装载我们自己的 v2ProPlus 权重，量 TTFT / RTF / 显存 / 音色相似度。

用法（必须用隔离 venv，里面有 gsv-tts-lite 与 torch cu121）：
    tts\\gsvenv\\Scripts\\python.exe tools\\gsv_lite_smoke.py
可选参数：
    --stream    额外测 infer_stream 的首包延迟
    --no-sv     跳过声纹相似度（省显存）
"""

from __future__ import annotations

import argparse
import imageio_ffmpeg
import json
import os
import subprocess
import sys
import time
import wave

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "tts", "gsv-models")
OUT_DIR = os.path.join(BASE, "preview", "gsv-lite")
GPT = os.path.join(BASE, "tts", "gptsovits", "GPT_weights_v2ProPlus", "Sandrone-e30.ckpt")
SOVITS = os.path.join(BASE, "tts", "gptsovits", "GPT_SoVITS", "SoVITS_weights_v2ProPlus", "sandrone4_e1_s128.pth")
SPK = os.path.join(BASE, "tts", "ref", "line4.wav")
PROMPT = os.path.join(BASE, "tts", "ref", "ref-cool-new.wav")
PROMPT_TEXT = "看来这地方没人管不代表不该有人管"
TEXT = "雪，茶凉了，我去换一杯。"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def to_wav(src: str, dst: str) -> str:
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "32000", dst],
        check=True,
    )
    return dst


def wav_seconds(path: str) -> float:
    with wave.open(path, "rb") as f:
        return f.getnframes() / float(f.getframerate())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--no-sv", action="store_true")
    ap.add_argument("--sdpa", choices=["math", "efficient", "cudnn", "auto"], default="math",
                    help="SDPA 后端；默认 math，因为 cuDNN/内存高效内核在 CUDA Graph 捕获里会报 operation not permitted")
    ap.add_argument("--no-graph", action="store_true", help="禁用 CUDA Graph 静态缓存（排查用）")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    import torch
    from torch.nn.attention import SDPBackend

    # 必须先打补丁再构造 TTS：t2s_model 在 import 时就把 SDPBACKEND 绑到自己命名空间里了
    if args.sdpa != "auto":
        backend = {
            "math": SDPBackend.MATH,
            "efficient": SDPBackend.EFFICIENT_ATTENTION,
            "cudnn": SDPBackend.CUDNN_ATTENTION,
        }[args.sdpa]
        import gsv_tts.Config as gcfg
        import gsv_tts.GPT_SoVITS.GPT.t2s_model as t2s

        gcfg.SDPBACKEND = backend
        t2s.SDPBACKEND = backend
        print(f"[sdpa] forced {args.sdpa}")

    from gsv_tts import TTS

    report = {}

    t0 = time.time()
    gpt_cache = [] if args.no_graph else None
    sovits_cache = [] if args.no_graph else None
    kwargs = dict(use_bert=True, use_flash_attn=False, models_dir=MODELS_DIR, always_load_sv=not args.no_sv)
    if args.no_graph:
        kwargs["gpt_cache"] = gpt_cache
        kwargs["sovits_cache"] = sovits_cache
    tts = TTS(**kwargs)
    report["init_s"] = round(time.time() - t0, 2)
    print(f"[init] {report['init_s']}s  device={tts.tts_config.device} dtype={tts.tts_config.dtype}")

    t0 = time.time()
    tts.load_gpt_model(GPT)
    report["load_gpt_s"] = round(time.time() - t0, 2)

    t0 = time.time()
    tts.load_sovits_model(SOVITS)
    report["load_sovits_s"] = round(time.time() - t0, 2)
    print(f"[load] gpt {report['load_gpt_s']}s  sovits {report['load_sovits_s']}s")

    # 预热：音色参考 + 风格参考都进缓存
    t0 = time.time()
    tts.cache_spk_audio(SPK)
    tts.cache_prompt_audio(PROMPT, PROMPT_TEXT)
    report["cache_s"] = round(time.time() - t0, 2)

    # 单句 infer
    wav_path = os.path.join(OUT_DIR, "infer.wav")
    t0 = time.time()
    audio = tts.infer(
        spk_audio_path=SPK,
        prompt_audio_path=PROMPT,
        prompt_audio_text=PROMPT_TEXT,
        text=TEXT,
    )
    report["infer_s"] = round(time.time() - t0, 2)
    audio.save(wav_path)
    report["audio_s"] = round(wav_seconds(wav_path), 2)
    report["rtf"] = round(report["infer_s"] / max(report["audio_s"], 0.01), 2)
    print(f"[infer] {report['infer_s']}s  audio {report['audio_s']}s  RTF {report['rtf']}")

    if args.stream:
        stream_path = os.path.join(OUT_DIR, "stream.wav")
        t_first = None
        chunks = []
        t0 = time.time()
        for clip in tts.infer_stream(
            spk_audio_path=SPK,
            prompt_audio_path=PROMPT,
            prompt_audio_text=PROMPT_TEXT,
            text=TEXT,
            stream_chunk=25,
            overlap_len=5,
            return_subtitles=True,
        ):
            if t_first is None:
                t_first = time.time() - t0
                subs = getattr(clip, "subtitles", None) or []
                report["subtitles"] = subs[:3]
            chunks.append(clip)
        report["ttft_s"] = round(t_first or -1, 3)
        report["stream_total_s"] = round(time.time() - t0, 2)
        # 拼成一个文件听
        import numpy as _np

        pcm = _np.concatenate([c.audio_data for c in chunks]) if chunks else _np.zeros(1, dtype=_np.float32)
        with wave.open(stream_path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(32000)
            f.writeframes((_np.clip(pcm, -1, 1) * 32767).astype("<i2").tobytes())
        report["stream_audio_s"] = round(wav_seconds(stream_path), 2)
        print(f"[stream] TTFT {report['ttft_s']}s  total {report['stream_total_s']}s  audio {report['stream_audio_s']}s")

    # 显存
    if torch.cuda.is_available():
        report["vram_peak_gb"] = round(torch.cuda.max_memory_allocated() / 1024**3, 2)
        report["vram_reserved_gb"] = round(torch.cuda.max_memory_reserved() / 1024**3, 2)
        print(f"[vram] peak {report['vram_peak_gb']}GB  reserved {report['vram_reserved_gb']}GB")

    # 声纹相似度：新合成 vs 我们烘好的固定台词
    if not args.no_sv:
        try:
            baked = to_wav(os.path.join(BASE, "assets", "voice", "voice-demo.m4a"), os.path.join(OUT_DIR, "baked.wav"))
            report["speaker_sim_vs_baked"] = round(float(tts.verify_speaker(wav_path, baked)), 4)
            report["speaker_sim_self"] = round(float(tts.verify_speaker(wav_path, SPK)), 4)
            print(f"[sv] vs 预制台词 {report['speaker_sim_vs_baked']}  vs 音色参考 {report['speaker_sim_self']}")
        except Exception as exc:  # noqa: BLE001
            report["speaker_sim_error"] = f"{type(exc).__name__}: {exc}"

    with open(os.path.join(OUT_DIR, "smoke.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
