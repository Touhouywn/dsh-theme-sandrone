"""从原声长音轨里挑三段不同气质的参考音，供 GPT-SoVITS 做「高能 / 温和 / 低语」分档。

参考音既决定音色，也决定"语气底色"：同一段语料里
  压着嗓子的段（能量低、谱平坦度高、过零率高）→ 合出来更轻、更气；
  放开的段（能量高、平坦度低、F0 稳）→ 合出来更冲、更亮。
所以这里同时看四个量来选，而不是只按响度：
  level(dBFS)、flatness(谱平坦度)、zcr(过零率)、voicing(自相关峰 = 浊音稳定度)
"""

import json
import os

import numpy as np
import soundfile as sf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get("SANDRONE_REF_SOURCE", os.path.join(BASE, "tts", "rvc", "sandrone40k.wav"))
OUT_DIR = os.path.join(BASE, "tts", "ref")
SR = 32000
WIN = 5.6
HOP = 0.4


def load_mono(path, sr):
    data, orig = sf.read(path, dtype="float32", always_2d=True)
    x = data.mean(axis=1)
    if orig != sr:
        n = int(round(len(x) * sr / float(orig)))
        idx = np.linspace(0, len(x) - 1, n)
        x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    return x


def features(seg):
    rms = float(np.sqrt(np.mean(np.square(seg)) + 1e-12))
    level = 20.0 * np.log10(rms + 1e-12)
    peak = float(np.max(np.abs(seg)))
    zcr = float(np.mean(np.abs(np.diff(np.sign(seg))) > 0))

    # 谱平坦度：噪声样（气声）平坦度高，浊音低。只取样 24 帧，够用且快。
    frame = 1024
    span = max(1, len(seg) - frame)
    step = max(frame * 4, span // 24)
    flats = []
    for i in range(0, span, step):
        w = seg[i:i + frame]
        if len(w) < frame:
            break
        spec = np.abs(np.fft.rfft(w * np.hanning(frame))) + 1e-9
        flats.append(float(np.exp(np.mean(np.log(spec))) / np.mean(spec)))
        if len(flats) >= 24:
            break
    flatness = float(np.median(flats)) if flats else 1.0

    # 浊音稳定度：只在中段 120ms 上做 FFT 自相关，避免整段 O(n^2)
    mid = len(seg) // 2
    half = int(0.06 * SR)
    clip = seg[max(0, mid - half): mid + half]
    n = 1 << int(np.ceil(np.log2(max(4, len(clip) * 2))))
    spec = np.fft.rfft(clip, n)
    ac = np.fft.irfft(spec * np.conj(spec), n)[:len(clip)]
    ac = ac / (ac[0] + 1e-9)
    lo, hi = int(SR / 400), min(int(SR / 70), len(ac) - 1)
    voicing = float(np.max(ac[lo:hi])) if hi > lo else 0.0

    return dict(level=level, peak=peak, zcr=zcr, flatness=flatness, voicing=voicing)


def main():
    if not os.path.exists(SRC):
        raise SystemExit("missing source: %s" % SRC)
    x = load_mono(SRC, SR)
    win = int(WIN * SR)
    hop = int(HOP * SR)

    cands = []
    for start in range(0, max(1, len(x) - win), hop):
        seg = x[start:start + win]
        if len(seg) < win:
            break
        f = features(seg)
        if f["peak"] < 0.02 or f["peak"] > 0.99:
            continue
        if f["level"] < -34:
            continue
        if f["voicing"] < 0.30:       # 太散，多半是气口/环境声
            continue
        cands.append((start, seg, f))

    if len(cands) < 5:
        raise SystemExit("not enough usable windows: %d" % len(cands))

    def zs(values):
        arr = np.array(values, dtype=np.float64)
        return (arr - arr.mean()) / (arr.std() + 1e-9)

    level_z = zs([c[2]["level"] for c in cands])
    flat_z = zs([c[2]["flatness"] for c in cands])
    zcr_z = zs([c[2]["zcr"] for c in cands])
    voi_z = zs([c[2]["voicing"] for c in cands])

    # 越"放开"分越高：响、亮、浊音稳；越"压着"分越低：轻、气、散
    score = level_z * 1.0 - flat_z * 0.9 - zcr_z * 0.8 + voi_z * 0.7
    order = np.argsort(score)

    picks = {
        "soft": cands[int(order[int(len(order) * 0.04)])],     # 最低的 4%
        "warm": cands[int(order[int(len(order) * 0.50)])],    # 中位
        "vivid": cands[int(order[int(len(order) * 0.97)])],   # 最高的 3%
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {}
    for tier, (start, seg, f) in picks.items():
        audio = seg.copy()
        fade = int(0.02 * SR)
        audio[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
        audio[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
        name = "ref-%s.wav" % tier
        sf.write(os.path.join(OUT_DIR, name), audio, SR, subtype="PCM_16")
        manifest[tier] = {
            "file": name,
            "at": round(start / float(SR), 2),
            "dbfs": round(f["level"], 1),
            "flatness": round(f["flatness"], 4),
            "zcr": round(f["zcr"], 4),
            "voicing": round(f["voicing"], 3),
            "score": round(float(score[cands.index(picks[tier])]), 2),
        }
        print("%-6s %-14s at %6.1fs  %6.1f dBFS  flat %.3f  zcr %.3f  voi %.2f  score %+.2f" % (
            tier, name, start / float(SR), f["level"], f["flatness"], f["zcr"], f["voicing"],
            score[cands.index(picks[tier])]))

    manifest["source"] = os.path.basename(SRC)
    manifest["candidates"] = len(cands)
    with open(os.path.join(OUT_DIR, "tiers.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print("candidates=%d  ->  %s" % (len(cands), os.path.join(OUT_DIR, "tiers.json")))


if __name__ == "__main__":
    main()
