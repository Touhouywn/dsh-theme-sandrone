"""从「3.2–8 秒且带准确原文」的片段里，挑出四个情绪池的参考音。

四个池不是靠猜：先把这批候选的韵律量出来，再按特征分配——
讽：音高幅度最大、语速最快；温：音高低、语速慢、起伏柔；
倦：能量起伏最小、音高最平；冷：居中的叙述底。

输出 tts/ref/ref-{cool,warm,tease,tired}.wav + tts/ref/pool_refs.json
"""

import io
import json
import os
import shutil

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(ROOT, "tts", "dataset", "list.txt")
REF_DIR = os.path.join(ROOT, "tts", "ref")
MIN_S, MAX_S = 3.2, 8.0


def measure(path):
    import librosa
    a, sr = sf.read(path, always_2d=False)
    if a.ndim > 1:
        a = a.mean(axis=1)
    a = a.astype(np.float32)
    a = a / (np.max(np.abs(a)) or 1.0)
    f0, _, _ = librosa.pyin(a, fmin=70, fmax=420, sr=sr, frame_length=1024, hop_length=256)
    f0 = f0[np.isfinite(f0)]
    hop = int(0.02 * sr)
    frames = max(1, len(a) // hop)
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(frames)])
    db = 20 * np.log10(rms + 1e-12)
    return {
        "dur": len(a) / sr,
        "f0_mean": float(np.mean(f0)),
        "f0_std": float(np.std(f0)),
        "f0_range": float(np.percentile(f0, 95) - np.percentile(f0, 5)),
        "erg_std": float(np.std(db)),
        "silence": float((db < np.percentile(db, 50) - 8).mean()),
    }


def main():
    rows = [line.rstrip("\n").split("|") for line in io.open(LIST, encoding="utf-8") if line.strip()]
    cands = []
    for row in rows:
        rel, text = row[0], row[-1]
        path = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(path):
            continue
        info = sf.info(path)
        if not (MIN_S <= info.duration <= MAX_S):
            continue
        st = measure(path)
        st.update({"rel": rel, "text": text, "cps": len(text) / max(0.2, st["dur"] * (1 - st["silence"]))})
        cands.append(st)
    print(f"候选 {len(cands)} 条（{MIN_S}-{MAX_S}s）：")
    for c in sorted(cands, key=lambda x: -x["f0_range"]):
        print(f"  {os.path.basename(c['rel'])}  {c['dur']:4.2f}s  f0={c['f0_mean']:5.1f}±{c['f0_std']:4.1f}"
              f" rng={c['f0_range']:5.1f} erg={c['erg_std']:5.2f} cps={c['cps']:4.1f}  {c['text'][:18]}")

    # 分配：四个指标各自取最极端的一条，且尽量不重复
    used = set()

    def pick(key, reverse, label):
        pool = [c for c in cands if c["rel"] not in used]
        if not pool:
            return None
        c = sorted(pool, key=lambda x: x[key], reverse=reverse)[0]
        used.add(c["rel"])
        print(f"[{label}] {os.path.basename(c['rel'])} {c[key]:.2f}  {c['text'][:20]}")
        return c

    tease = pick("f0_range", True, "讽")
    tired = pick("erg_std", False, "倦")
    warm = pick("f0_mean", False, "温")
    cool = pick("f0_range", False, "冷")

    mapping = {"cool": cool, "warm": warm, "tease": tease, "tired": tired}
    refs = {}
    for name, c in mapping.items():
        if not c:
            continue
        src = os.path.join(ROOT, c["rel"].replace("/", os.sep))
        dst = os.path.join(REF_DIR, f"ref-{name}.wav")
        shutil.copyfile(src, dst)
        refs[name] = {
            "file": f"ref-{name}.wav",
            "text": c["text"],
            "dur": round(c["dur"], 2),
            "speed": {"cool": 0.95, "warm": 0.92, "tease": 0.98, "tired": 0.90}[name],
        }
    with io.open(os.path.join(REF_DIR, "pool_refs.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(refs, fh, ensure_ascii=False, indent=2)
    print(json.dumps(refs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
