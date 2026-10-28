"""Sandrone GPT-SoVITS API launcher.

Wraps the upstream api_v2.py with two local patches so it can run offline on this
machine: fast-langdetect has no model cache here, so language detection is pinned
to Chinese (the plugin only ever sends Chinese text).
"""

import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "gptsovits")

os.chdir(REPO)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "GPT_SoVITS"))

os.environ.setdefault("FTLANG_CACHE", os.path.join(REPO, ".ftlang"))
os.makedirs(os.environ["FTLANG_CACHE"], exist_ok=True)

try:  # split-lang asks for a list of {lang, score}
    import split_lang.detect_lang.detector as detector

    detector.fast_lang_detect = lambda text, **kwargs: "zh"
    detector.detect_lang_combined = lambda text, **kwargs: "zh"
except Exception as error:  # pragma: no cover - best effort
    print(f"[gs_api] langdetect patch skipped: {error}", flush=True)

try:
    import fast_langdetect

    fast_langdetect.detect = lambda text, *args, **kwargs: [{"lang": "zh", "score": 1.0}]
    fast_langdetect.detect_language = lambda text, *args, **kwargs: "zh"
except Exception as error:  # pragma: no cover
    print(f"[gs_api] fast_langdetect patch skipped: {error}", flush=True)

sys.argv = ["api_v2.py", "-a", "127.0.0.1", "-p", "9880"]
runpy.run_path(os.path.join(REPO, "api_v2.py"), run_name="__main__")
