"""GSV-TTS-Lite 常驻服务。

只做一件事：把 Lite 推理包装成 HTTP，供 DSH 插件宿主调用。
  GET  /health                      -> 状态
  POST /infer   {text,pool,speed?}  -> audio/wav (32k mono 16-bit)
  POST /stream  {text,pool}         -> chunked raw PCM (s16le, 32k mono)

必须用隔离 venv 运行：
  tts\\gsvenv\\Scripts\\python.exe tts\\gsv_lite_server.py --port 9882
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "tts", "gsv-models")
GPT = os.path.join(BASE, "tts", "gptsovits", "GPT_weights_v2ProPlus", "Sandrone-e30.ckpt")
SOVITS = os.path.join(
    BASE, "tts", "gptsovits", "GPT_SoVITS", "SoVITS_weights_v2ProPlus", "sandrone4_e1_s128.pth"
)
# 音色（timbre）与风格（style）彻底分开：
#   timbre 决定「是谁在说」，style 决定「用什么念法说」，两者互不干扰。
TIMBRES = {
    "sandrone": {"spk": os.path.join(BASE, "tts", "ref", "line4.wav"), "label": "默认（第 4 段原声）"},
    "alt-a": {"spk": os.path.join(BASE, "tts", "ref", "line3.wav"), "label": "备选 A（第 3 段原声）"},
    "alt-b": {"spk": os.path.join(BASE, "tts", "ref", "line5.wav"), "label": "备选 B（第 5 段原声）"},
}
DEFAULT_TIMBRE = "sandrone"
SPK = TIMBRES[DEFAULT_TIMBRE]["spk"]

# 四个情绪池：参考音决定「念法」，音色由 SPK 固定
POOLS = {
    "cool": {"ref": os.path.join(BASE, "tts", "ref", "ref-cool-new.wav"), "text": "看来这地方没人管不代表不该有人管"},
    "warm": {"ref": os.path.join(BASE, "tts", "ref", "ref-warm.wav"), "text": "去,先给他们上些前菜。"},
    "tease": {"ref": os.path.join(BASE, "tts", "ref", "ref-warm.wav"), "text": "去,先给他们上些前菜。"},
    "tired": {"ref": os.path.join(BASE, "tts", "ref", "ref-soft.wav"), "text": "你叫我下手居然这么重别过来添乱没看见我这么"},
}

CN_LANGS = {
    "zh", "wuu", "yue", "nan", "hak", "cmn", "lzh", "gan", "hsn",
    "cdo", "czh", "cjy", "cpx", "czo", "mnp", "csp",
}

_tts = None
_lock = threading.Lock()
_stats = {"calls": 0, "errors": 0, "lastMs": 0}


def _patch_langsegment() -> None:
    """langid 会把「语音回路已接通」判成吴语(wuu)，LangSegment 只保留 zh/en/ja/ko，整段被静默丢弃。

    把中文族标签统一折算成 zh，避免任意输入掉字。
    """
    from gsv_tts.LangSegment import LangSegment

    orig = LangSegment._saveData

    def _save(words, language, text):
        if str(language).split("|")[0] in CN_LANGS:
            language = "zh"
        return orig(words, language, text)

    LangSegment._saveData = staticmethod(_save)


def _patch_sdpa(backend_name: str) -> None:
    """CUDA Graph 捕获期间 cuDNN SDPA 会报 operation not permitted，必须提前换成别的后端。"""
    if backend_name == "auto":
        return
    import torch
    from torch.nn.attention import SDPBackend

    backend = {
        "math": SDPBackend.MATH,
        "efficient": SDPBackend.EFFICIENT_ATTENTION,
        "cudnn": SDPBackend.CUDNN_ATTENTION,
    }[backend_name]
    import gsv_tts.Config as gcfg
    import gsv_tts.GPT_SoVITS.GPT.t2s_model as t2s

    gcfg.SDPBACKEND = backend
    t2s.SDPBACKEND = backend
    print(f"[sdpa] {backend_name}", flush=True)


def boot(backend: str, only: list[str] | None) -> None:
    global _tts
    os.makedirs(MODELS_DIR, exist_ok=True)
    _patch_sdpa(backend)
    _patch_langsegment()

    from gsv_tts import TTS

    t0 = time.time()
    tts = TTS(use_bert=True, use_flash_attn=False, models_dir=MODELS_DIR, always_load_sv=True)
    tts.load_gpt_model(GPT)
    tts.load_sovits_model(SOVITS)
    for name, info in TIMBRES.items():
        tts.cache_spk_audio(info["spk"])
    pools = only or list(POOLS)
    for name in pools:
        info = POOLS[name]
        tts.cache_prompt_audio(info["ref"], info["text"])
    _tts = tts
    print(f"[boot] ready in {time.time() - t0:.1f}s pools={pools}", flush=True)


def resolve(timbre: str, style: str):
    tb = TIMBRES.get(str(timbre or DEFAULT_TIMBRE)) or TIMBRES[DEFAULT_TIMBRE]
    st = POOLS.get(str(style or "cool")) or POOLS["cool"]
    return tb["spk"], st


def synth_wav(text: str, pool: str, speed: float | None, timbre: str = DEFAULT_TIMBRE,
              temperature: float = 0.7, top_k: int = 15) -> bytes:
    spk, info = resolve(timbre, pool)
    kwargs = dict(
        spk_audio_path=spk,
        prompt_audio_path=info["ref"],
        prompt_audio_text=info["text"],
        text=text,
        temperature=float(temperature),
        top_k=int(top_k),
    )
    if speed:
        kwargs["speed"] = speed
    with _lock:
        audio = _tts.infer(**kwargs)
    import numpy as np

    pcm = (np.clip(audio.audio_data, -1, 1) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(int(getattr(audio, "sample_rate", 32000) or 32000))
        f.writeframes(pcm.tobytes())
    return buf.getvalue()


def synth_stream(text: str, pool: str, timbre: str = DEFAULT_TIMBRE,
                 temperature: float = 0.7, top_k: int = 15):
    spk, info = resolve(timbre, pool)
    gen = _tts.infer_stream(
        spk_audio_path=spk,
        prompt_audio_path=info["ref"],
        prompt_audio_text=info["text"],
        text=text,
        stream_chunk=25,
        overlap_len=5,
        temperature=float(temperature),
        top_k=int(top_k),
    )
    for clip in gen:
        yield clip


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # noqa: A003
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/health"):
            import torch

            self._json(200, {
                "ok": _tts is not None,
                "device": str(getattr(getattr(_tts, "tts_config", None), "device", "?")),
                "pools": list(POOLS),
                "timbre": DEFAULT_TIMBRE,
                "timbres": {k: v["label"] for k, v in TIMBRES.items()},
                "vramG": round(torch.cuda.memory_allocated() / 1024 ** 3, 2) if torch.cuda.is_available() else 0,
                "stats": _stats,
            })
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        try:
            length = int(self.headers.get("content-length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:  # noqa: BLE001
            self._json(400, {"error": f"bad json: {exc}"})
            return

        text = str(payload.get("text") or "").strip()
        pool = str(payload.get("pool") or "cool")
        if self.path.startswith("/verify"):
            try:
                score = float(_tts.verify_speaker(str(payload.get("a")), str(payload.get("b"))))
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
                return
            self._json(200, {"score": round(score, 4)})
            return

        if not text:
            self._json(400, {"error": "empty text"})
            return
        if _tts is None:
            self._json(503, {"error": "model not ready"})
            return

        t0 = time.time()
        _stats["calls"] += 1
        try:
            if self.path.startswith("/stream"):
                self.send_response(200)
                self.send_header("content-type", "application/octet-stream")
                self.send_header("transfer-encoding", "chunked")
                self.send_header("x-sample-rate", "32000")
                self.end_headers()
                for clip in synth_stream(text, pool, payload.get("timbre"),
                                     payload.get("temperature") or 0.7,
                                     payload.get("top_k") or 15):
                    data = clip.audio_data
                    pcm = (data * 32767).clip(-32768, 32767).astype("<i2").tobytes()
                    if not pcm:
                        continue
                    self.wfile.write(f"{len(pcm):X}\r\n".encode())
                    self.wfile.write(pcm)
                    self.wfile.write(b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            else:
                wav = synth_wav(text, pool, payload.get("speed"), payload.get("timbre"),
                            payload.get("temperature") or 0.7,
                            payload.get("top_k") or 15)
                self.send_response(200)
                self.send_header("content-type", "audio/wav")
                self.send_header("content-length", str(len(wav)))
                self.end_headers()
                self.wfile.write(wav)
            _stats["lastMs"] = int((time.time() - t0) * 1000)
        except Exception as exc:  # noqa: BLE001
            _stats["errors"] += 1
            import traceback

            traceback.print_exc()
            try:
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
            except Exception:  # noqa: BLE001
                pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9882)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--sdpa", choices=["math", "efficient", "cudnn", "auto"], default="efficient")
    ap.add_argument("--only", default="", help="只预缓存这几个池，逗号分隔（排查用）")
    args = ap.parse_args()

    only = [p.strip() for p in args.only.split(",") if p.strip()] or None
    boot(args.sdpa, only)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[listen] http://{args.host}:{args.port}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
