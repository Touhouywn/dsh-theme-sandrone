"""衡量「音色稳定性」：声纹相似度矩阵 + 解耦风格的四池试听样本。

背景：我们现有的 48 条预制台词是 api_v2 烘的，参考音既是音色又是风格，
所以不同池之间的音色本来就存在漂移。GSV-TTS-Lite 把两者拆开
（spk_audio=音色、prompt_audio=风格），理论上同一音色参考下四池应当更像同一个人。

输出：
  preview/gsv-lite/sv-matrix.json     现有预制台词的音色相似度矩阵（基线漂移量）
  preview/gsv-lite/pool-{warm,cool,tease,tired}.wav   四池同句、同音色、不同风格
  preview/gsv-lite/pool-matrix.json   四池样本两两相似度（解耦后的稳定性）
"""

from __future__ import annotations

import imageio_ffmpeg
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "preview", "gsv-lite")
MODELS = os.path.join(BASE, "tts", "gsv-models")
GPT = os.path.join(BASE, "tts", "gptsovits", "GPT_weights_v2ProPlus", "Sandrone-e30.ckpt")
SOVITS = os.path.join(BASE, "tts", "gptsovits", "GPT_SoVITS", "SoVITS_weights_v2ProPlus", "sandrone4_e1_s128.pth")
SPK = os.path.join(BASE, "tts", "ref", "line4.wav")
REF = os.path.join(BASE, "tts", "ref")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# 四个风格参考（对应我们的四池）
POOL_TEXT = json.load(open(os.path.join(BASE, "tts", "ref", "pool_text.json"), encoding="utf-8"))
STYLES = {
    "cool": ("ref-cool-new.wav", "看来这地方没人管不代表不该有人管"),
    "warm": ("ref-warm.wav", POOL_TEXT["ref-warm.wav"]),
    "tease": ("ref-vivid.wav", POOL_TEXT["ref-vivid.wav"]),
    "tired": ("ref-soft.wav", POOL_TEXT["ref-soft.wav"]),
}
TEXT = "雪，茶凉了，我去换一杯。"

BAKED = ["welcome", "greet-night", "voice-demo", "react-hello", "react-thanks"]


def to_wav(src, dst):
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "32000", dst], check=True)
    return dst


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import torch
    from torch.nn.attention import SDPBackend
    import gsv_tts.Config as gcfg
    import gsv_tts.GPT_SoVITS.GPT.t2s_model as t2s

    gcfg.SDPBACKEND = SDPBackend.MATH
    t2s.SDPBACKEND = SDPBackend.MATH
    from gsv_tts import TTS

    tts = TTS(use_bert=True, use_flash_attn=False, models_dir=MODELS, always_load_sv=True)
    tts.load_gpt_model(GPT)
    tts.load_sovits_model(SOVITS)
    tts.cache_spk_audio(SPK)

    # 1) 现有预制台词之间的音色漂移（基线）
    baked_wavs = {}
    for key in BAKED:
        src = os.path.join(BASE, "assets", "voice", f"{key}.m4a")
        dst = os.path.join(OUT, f"baked-{key}.wav")
        baked_wavs[key] = to_wav(src, dst)

    base_matrix = {}
    for a in BAKED:
        base_matrix[a] = {}
        for b in BAKED:
            base_matrix[a][b] = round(float(tts.verify_speaker(baked_wavs[a], baked_wavs[b])), 4)
    with open(os.path.join(OUT, "sv-matrix.json"), "w", encoding="utf-8") as f:
        json.dump(base_matrix, f, ensure_ascii=False, indent=2)

    # 2) 四池同句、同音色、不同风格
    pool_wavs = {}
    for pool, (ref_name, ref_text) in STYLES.items():
        clip = tts.infer(
            spk_audio_path=SPK,
            prompt_audio_path=os.path.join(REF, ref_name),
            prompt_audio_text=ref_text,
            text=TEXT,
        )
        path = os.path.join(OUT, f"pool-{pool}.wav")
        clip.save(path)
        pool_wavs[pool] = path

    pool_matrix = {}
    for a in pool_wavs:
        pool_matrix[a] = {}
        for b in pool_wavs:
            pool_matrix[a][b] = round(float(tts.verify_speaker(pool_wavs[a], pool_wavs[b])), 4)
    with open(os.path.join(OUT, "pool-matrix.json"), "w", encoding="utf-8") as f:
        json.dump(pool_matrix, f, ensure_ascii=False, indent=2)

    # 3) 同一句：预制版本 vs Lite 版本（同文本，供 A/B 试听）
    demo_text = "语音回路已接通。……听得到吗。"
    clip = tts.infer(spk_audio_path=SPK, prompt_audio_path=os.path.join(REF, "ref-cool-new.wav"),
                     prompt_audio_text=STYLES["cool"][1], text=demo_text)
    clip.save(os.path.join(OUT, "ab-lite.wav"))
    to_wav(os.path.join(BASE, "assets", "voice", "voice-demo.m4a"), os.path.join(OUT, "ab-baked.wav"))

    avg_base = sum(v for k, row in base_matrix.items() for kk, v in row.items() if k != kk) / max(
        1, sum(1 for k, row in base_matrix.items() for kk in row if k != kk))
    avg_pool = sum(v for k, row in pool_matrix.items() for kk, v in row.items() if k != kk) / max(
        1, sum(1 for k, row in pool_matrix.items() for kk in row if k != kk))

    print(json.dumps({
        "baked_pairwise_avg": round(avg_base, 4),
        "pool_pairwise_avg": round(avg_pool, 4),
        "baked_matrix": base_matrix,
        "pool_matrix": pool_matrix,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
