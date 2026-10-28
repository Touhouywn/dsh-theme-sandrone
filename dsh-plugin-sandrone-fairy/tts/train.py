"""Drive GPT-SoVITS v2ProPlus fine-tuning on the sliced Sandrone dataset.

Steps (run one at a time with --stage):
    prep    : 1a text features -> 1b hubert -> 1c semantic tokens
    s2      : SoVITS training (init from the user's e16 weights)
    s1      : GPT training (init from the user's e30 weights)

Everything is logged to tts/dataset/train.log.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(BASE, "tts", "gptsovits")
GS = os.path.join(REPO, "GPT_SoVITS")
PREP = os.path.join(GS, "prepare_datasets")
EXP = os.environ.get("SANDRONE_EXP", "sandrone2")
LOG = os.path.join(BASE, "tts", "dataset", "train.log")
LIST = os.environ.get("SANDRONE_LIST") or os.path.join(BASE, "tts", "dataset", "list.txt")
WAVS = os.path.join(BASE, "tts", "dataset", "wavs")

USER_WEIGHTS = r"D:\AI\桑多涅"
S2_INIT = os.path.join(GS, "SoVITS_weights_v2ProPlus", "Sandrone_e16_s320.pth")
S1_INIT = os.path.join(GS, "GPT_weights_v2ProPlus", "Sandrone-e30.ckpt")
S2_BASE = os.path.join(GS, "pretrained_models", "v2Pro", "s2Gv2ProPlus.pth")
S2_DISC = os.path.join(GS, "pretrained_models", "v2Pro", "s2Dv2ProPlus.pth")
S1_BASE = os.path.join(GS, "pretrained_models", "s1v3.ckpt")
BERT = os.path.join(GS, "pretrained_models", "chinese-roberta-wwm-ext-large")


def log(message):
    stamp = time.strftime("%H:%M:%S")
    line = "[%s] %s" % (stamp, message)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def base_env():
    """GPT_SoVITS 的脚本靠 sys.path 找 text/tools/feature，必须显式塞进去。"""
    paths = [GS, REPO, os.path.join(REPO, "third_party", "Matcha-TTS"), os.path.join(GS, "pretrained_models")]
    existing = os.environ.get("PYTHONPATH", "")
    if existing:
        paths.append(existing)
    env = {"PYTHONPATH": os.pathsep.join(paths)}
    # my_utils.load_audio / whisper 都会壳调 ffmpeg，PATH 里必须能找到它
    ffmpeg_dir = r"C:\Program Files (x86)\Lenovo\LegionZone\2.0.23.3251\SEGamingAI\services\editor"
    if os.path.isdir(ffmpeg_dir):
        env["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    return env


def run(cmd, env=None, cwd=None):
    log("RUN " + " ".join(os.path.basename(part) if index else part for index, part in enumerate(cmd)))
    merged = dict(os.environ)
    merged["PYTHONIOENCODING"] = "utf-8"
    merged["PYTHONUNBUFFERED"] = "1"
    merged.update(base_env())
    if env:
        merged.update(env)
    with open(LOG, "a", encoding="utf-8") as handle:
        process = subprocess.Popen(
            cmd, env=merged, cwd=cwd or GS, stdout=handle, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return process.wait()


def prep_env():
    opt = os.path.join(GS, "logs", EXP)
    os.makedirs(opt, exist_ok=True)
    return {
        "inp_text": LIST,
        "inp_wav_dir": WAVS,
        "exp_name": EXP,
        "i_part": "0",
        "all_parts": "1",
        "opt_dir": opt,
        "bert_pretrained_dir": BERT,
        "cnhubert_base_dir": os.path.join(GS, "pretrained_models", "chinese-hubert-base"),
        "pretrained_s2G": S2_BASE,
        "s2config_path": os.path.join(GS, "configs", "s2v2ProPlus.json"),
        "is_half": "True",
        "version": "v2ProPlus",
        "python": sys.executable,
    }


def stage_prep():
    env = prep_env()
    env["sv_path"] = os.path.join(GS, "pretrained_models", "sv", "pretrained_eres2netv2w24s4ep4.ckpt")
    for script in ("1-get-text.py", "2-get-hubert-wav32k.py", "2-get-sv.py", "3-get-semantic.py"):
        code = run([sys.executable, os.path.join(PREP, script)], env=env, cwd=REPO)
        log("%s -> exit %s" % (script, code))
        if code != 0:
            return code

    opt = os.path.join(GS, "logs", EXP)
    for part, final in (("2-name2text-0.txt", "2-name2text.txt"),
                        ("6-name2semantic-0.tsv", "6-name2semantic.tsv")):
        src = os.path.join(opt, part)
        dst = os.path.join(opt, final)
        if os.path.exists(src):
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
            log("renamed %s -> %s" % (part, final))
    return 0


def stage_s2(epochs, batch):
    """在官方 s2v2ProPlus.json 上只改训练参数，避免模型结构与权重不匹配。"""
    opt = os.path.join(GS, "logs", EXP)
    with open(os.path.join(GS, "configs", "s2v2ProPlus.json"), encoding="utf-8") as handle:
        config = json.load(handle)

    train = config.setdefault("train", {})
    train.update({
        "epochs": epochs,
        "batch_size": batch,
        "fp16_run": True,
        "grad_ckpt": True,
        "save_every_epoch": 1,
        "if_save_every_weights": True,
        "if_save_latest": True,
        "log_interval": 20,
        "eval_interval": 100,
        "pretrained_s2G": S2_INIT if os.path.exists(S2_INIT) else S2_BASE,
        "pretrained_s2D": S2_DISC,
        "s2config_path": os.path.join(GS, "configs", "s2v2ProPlus.json"),
        "gpu_numbers": "0",
    })
    config.setdefault("model", {})["version"] = "v2ProPlus"
    config.setdefault("data", {})["exp_dir"] = opt
    config["s2_ckpt_dir"] = opt
    config["save_weight_dir"] = os.path.join(GS, "SoVITS_weights_v2ProPlus")
    config["name"] = EXP

    path = os.path.join(GS, "configs", "s2_%s.json" % EXP)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
    log("s2 config -> %s (epochs=%d batch=%d)" % (path, epochs, batch))
    return run([sys.executable, os.path.join(GS, "s2_train.py"), "--config", path])


def stage_s1(epochs, batch):
    source = os.path.join(GS, "configs", "s1longer-v2.yaml")
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    opt = os.path.join(GS, "logs", EXP)
    output_dir = os.path.join(GS, "logs", EXP + "_s1")
    os.makedirs(output_dir, exist_ok=True)
    text = text.replace("/path/to/xxx/2-name2text.txt", os.path.join(opt, "2-name2text.txt").replace("\\", "/"))
    text = text.replace("/path/to/xxx/6-name2semantic.tsv", os.path.join(opt, "6-name2semantic.tsv").replace("\\", "/"))
    text = text.replace("/path/to/xxx/3-bert", os.path.join(opt, "3-bert").replace("\\", "/"))
    text = text.replace("/path/to/xxx/", (output_dir + "/").replace("\\", "/"))
    text = text.replace("pretrained_s1: GPT_SoVITS/pretrained_models/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt",
                        "pretrained_s1: " + (S1_INIT if os.path.exists(S1_INIT) else S1_BASE).replace("\\", "/"))
    for key, value in (("batch_size", batch), ("epochs", epochs)):
        import re
        text = re.sub(r"^(%s:).*$" % key, r"\1 %s" % value, text, flags=re.M)
    path = os.path.join(GS, "configs", "s1_%s.yaml" % EXP)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return run([sys.executable, os.path.join(GS, "s1_train.py"), "--config", path])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="prep", choices=["prep", "s2", "s1"])
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch", type=int, default=2)
    args = parser.parse_args()

    log("=== stage %s (epochs=%d batch=%d)" % (args.stage, args.epochs, args.batch))
    if not os.path.exists(LIST):
        log("missing list: %s" % LIST)
        return 2
    if args.stage == "prep":
        return stage_prep()
    if args.stage == "s2":
        return stage_s2(args.epochs, args.batch)
    return stage_s1(args.epochs, args.batch)


if __name__ == "__main__":
    sys.exit(main())
