"""Point GPT-SoVITS at the chosen Sandrone weights and (re)start its API.

The plugin talks to the HTTP API, so switching voices = rewrite the custom
section of ``tts_infer.yaml`` + restart the server.  Weight files are kept
side by side, nothing is overwritten.
"""

import os
import subprocess
import sys
import time
import urllib.request

import yaml

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GS = os.path.join(BASE, "tts", "gptsovits", "GPT_SoVITS")
CFG = os.path.join(GS, "configs", "tts_infer.yaml")
API = "http://127.0.0.1:9880"

WEIGHTS = {
    "e1": os.path.join(GS, "SoVITS_weights_v2ProPlus", "sandrone4_e1_s128.pth"),
    "e3": os.path.join(GS, "SoVITS_weights_v2ProPlus", "sandrone4_e3_s384.pth"),
    "e6": os.path.join(GS, "SoVITS_weights_v2ProPlus", "sandrone4_e6_s768.pth"),
    "e16": os.path.join(BASE, "tts", "gptsovits", "SoVITS_weights_v2ProPlus", "Sandrone_e16_s320.pth"),
}
GPT = os.path.join(BASE, "tts", "gptsovits", "GPT_weights_v2ProPlus", "Sandrone-e30.ckpt")


def set_weights(tag):
    path = WEIGHTS[tag]
    if not os.path.exists(path):
        raise SystemExit("missing weights: %s" % path)
    data = yaml.safe_load(open(CFG, encoding="utf-8"))
    custom = data.setdefault("custom", {})
    custom["vits_weights_path"] = path
    custom["t2s_weights_path"] = GPT
    custom["version"] = "v2ProPlus"
    custom["device"] = "cuda"
    custom["is_half"] = True
    yaml.safe_dump(data, open(CFG, "w", encoding="utf-8"), allow_unicode=True, sort_keys=True)
    print("weights ->", tag, os.path.basename(path), flush=True)
    return path


def stop_server():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "$c = Get-NetTCPConnection -LocalPort 9880 -State Listen -ErrorAction SilentlyContinue; "
         "if ($c) { $c.OwningProcess | Select-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force } }"],
        capture_output=True, text=True,
    )
    time.sleep(1)
    print("server stopped", flush=True)


def wait_ready(timeout=180):
    started = time.time()
    while time.time() - started < timeout:
        try:
            with urllib.request.urlopen(API + "/openapi.json", timeout=3) as res:
                if res.status < 500:
                    print("api ready in %.1fs" % (time.time() - started), flush=True)
                    return True
        except Exception:
            time.sleep(2)
    print("api not ready after %ss" % timeout, flush=True)
    return False


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "e1"
    set_weights(tag)
    stop_server()
    python = os.path.join(BASE, "tts", "rvcenv", "Scripts", "python.exe")
    if not os.path.exists(python):
        python = sys.executable
    log = open(os.path.join(BASE, "tts", "gs_server.log"), "a", encoding="utf-8")
    subprocess.Popen(
        [python, os.path.join(BASE, "tts", "gs_api.py")],
        cwd=BASE, stdout=log, stderr=log,
        creationflags=0x00000008,  # DETACHED_PROCESS
    )
    wait_ready()


if __name__ == "__main__":
    main()
