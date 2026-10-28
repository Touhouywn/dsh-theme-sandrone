"""Build the hand-off zip: code + runtime assets, no engines, no caches."""

import io
import json
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION = json.loads(io.open(os.path.join(ROOT, "package.json"), encoding="utf-8").read())["version"]
OUT = os.path.join(os.path.dirname(ROOT), f"sandrone-fairy-{_VERSION}.zip")

FILES = [
    "package.json", "index.js", "client.js", "cordis.patch.yml", "icon.svg",
    "locale/en.json", "locale/zh.json",
]
GLOBS = [
    ("assets", (".jpg", ".png", ".webp")),
    ("assets/voice", (".m4a",)),
    ("tts", (".py", ".json", ".txt")),
    ("tts/ref", (".wav",)),
    ("tools", (".mjs", ".ps1", ".md", ".py")),
    ("preview", (".png",)),
    ("ui", (".html",)),
    ("docs", (".md",)),
    ("docs/img", (".png",)),
]
SINGLE = [
    "install.ps1", "uninstall.ps1", "README.md", "CHANGELOG.md", "NOTICE.md",
    "LICENSE", "INTEGRATION.md", ".gitignore", "install.sh",
]
SKIP_NAME = {"source.wav", "jieba.cache", "gsv_install.log", "pack_tiers.log"}
SKIP_DIR = {"gptsovits", "dataset", "dataset2", "dataset_old", "rvc", "rvcenv", "cache", "tmp_voice"}


def collect():
    paths = []
    for rel in FILES + SINGLE:
        full = os.path.join(ROOT, rel.replace("/", os.sep))
        if os.path.isfile(full):
            paths.append(rel)
    for folder, exts in GLOBS:
        base = os.path.join(ROOT, folder.replace("/", os.sep))
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            full = os.path.join(base, name)
            if not os.path.isfile(full):
                continue
            if not name.lower().endswith(exts):
                continue
            if name in SKIP_NAME:
                continue
            paths.append(folder + "/" + name)
    return paths


def main():
    entries = collect()
    if os.path.exists(OUT):
        os.remove(OUT)
    total = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel in entries:
            full = os.path.join(ROOT, rel.replace("/", os.sep))
            archive.write(full, rel)
            total += os.path.getsize(full)
    with zipfile.ZipFile(OUT) as archive:
        names = archive.namelist()
    print("zip:", OUT)
    print("files:", len(names), " raw:", round(total / 1048576, 2), "MB",
          " zip:", round(os.path.getsize(OUT) / 1048576, 2), "MB")
    print("refs:", [n for n in names if n.startswith("tts/ref/")])
    print("voices:", len([n for n in names if n.startswith("assets/voice/")]))
    with zipfile.ZipFile(OUT) as archive:
        print("version:", json.loads(archive.read("package.json"))["version"])


if __name__ == "__main__":
    main()
