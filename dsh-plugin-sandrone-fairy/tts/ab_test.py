"""Render one sentence with several SoVITS weights for an A/B listen.

Runs the model offline (no api_v2 server), so it can be used right after a
training run.  Each weight produces one m4a in preview/.

Usage:
    python tts/ab_test.py --weights a.pth b.pth --text "……哼，回来了。"
"""

import argparse
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS = os.path.join(BASE, "tts", "gptsovits", "GPT_SoVITS")
REPO = os.path.join(BASE, "tts", "gptsovits")
FFMPEG = r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor\ffmpeg.exe"

DEFAULT_TEXT = "……哼，回来了。我又没在等你。……茶还热着，坐下吧。"
REF = os.path.join(BASE, "tts", "ref", "line4.wav")


def patch_langdetect():
    """fast-langdetect has no model cache offline; pin everything to Chinese."""
    os.environ.setdefault("FTLANG_CACHE", os.path.join(REPO, ".ftlang"))
    os.makedirs(os.environ["FTLANG_CACHE"], exist_ok=True)
    try:
        import fast_langdetect

        fast_langdetect.detect = lambda text, *a, **k: [{"lang": "zh", "score": 1.0}]
        fast_langdetect.detect_language = lambda text, *a, **k: "zh"
    except Exception as error:  # pragma: no cover
        print("[ab_test] fast_langdetect patch skipped: %s" % error, flush=True)
    try:
        import split_lang.detect_lang.detector as detector

        detector.fast_lang_detect = lambda text, *a, **k: "zh"
        detector.detect_lang_combined = lambda text, *a, **k: "zh"
        detector.possible_detection_list = lambda text, *a, **k: ["zh"]
    except Exception as error:  # pragma: no cover
        print("[ab_test] split_lang patch skipped: %s" % error, flush=True)


def prepare_env():
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ["PATH"] = os.path.join(BASE, "tts", "ffmpeg") + os.pathsep + os.environ.get("PATH", "")
    sys.path.insert(0, REPO)
    sys.path.insert(0, GS)
    os.chdir(REPO)
    patch_langdetect()


def load(reference, weights, gpt):
    from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config

    cfg = TTS_Config(os.path.join(GS, "configs", "tts_infer.yaml"))
    cfg.device = "cuda"
    cfg.is_half = True
    cfg.t2s_weights_path = gpt
    cfg.vits_weights_path = weights
    tts = TTS(cfg)
    return tts


def synth(tts, text, out_m4a, reference):
    req = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": reference,
        "prompt_text": "",
        "prompt_lang": "zh",
        "top_k": 15,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "cut5",
        "batch_size": 1,
        "speed_factor": 0.95,
        "seed": 42,
        "parallel_infer": True,
        "repetition_penalty": 1.35,
    }
    wav_tmp = out_m4a.replace(".m4a", ".wav")
    import soundfile as sf

    wrote = 0
    for sr_out, audio in tts.run(req):
        if audio is None or len(audio) == 0:
            continue
        sf.write(wav_tmp, audio, sr_out)
        wrote += 1
    if not wrote:
        raise RuntimeError("no audio produced")
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", wav_tmp,
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "44100",
         "-c:a", "aac", "-b:a", "128k", out_m4a],
        check=True,
    )
    os.remove(wav_tmp)
    return os.path.getsize(out_m4a)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", nargs="+", required=True)
    parser.add_argument("--gpt", default=os.path.join(GS, "GPT_weights_v2ProPlus", "Sandrone-e30.ckpt"))
    parser.add_argument("--ref", default=REF)
    parser.add_argument("--text", default=DEFAULT_TEXT)
    parser.add_argument("--tag", default="")
    args = parser.parse_args()

    prepare_env()
    tts = load(args.ref, args.weights[0], args.gpt)
    for path in args.weights:
        name = os.path.basename(path).replace(".pth", "")
        label = "%s%s" % (args.tag, name)
        out = os.path.join(BASE, "preview", "ab-%s.m4a" % label)
        tts.init_vits_weights(path)
        size = synth(tts, args.text, out, args.ref)
        print("%-34s %5dKB  %s" % (label, size // 1024, out), flush=True)


if __name__ == "__main__":
    main()
