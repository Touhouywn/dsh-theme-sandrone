#!/usr/bin/env python3
"""Build the installable release zip and its SHA-256.

    python tools/build-release.py

Reads the version from dsh-theme-sandrone/package.json, walks the repository,
skips git/research/build directories, and writes:

    dist/dsh-theme-sandrone-<version>.zip
    dist/SHA256SUMS-v<version>.txt

The archive has one top-level directory so extracting it never scatters files
into the current folder. It contains the theme, the sidebar hub, the persona
plugin, docs, preview and build tooling, but no .git data and no local research
material.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SKIP_DIRS = {".git", ".research", "dist", "node_modules", "__pycache__", ".venv"}
SKIP_FILES = {".gitignore", ".gitattributes", ".editorconfig", "Thumbs.db", ".DS_Store"}


def version() -> str:
    data = json.loads((ROOT / "dsh-theme-sandrone" / "package.json").read_text(encoding="utf-8"))
    return str(data["version"])


def collect() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in SKIP_FILES or path.name.endswith((".build.wav", ".pyc")):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    version_text = version()
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"dsh-theme-sandrone-{version_text}.zip"
    sum_file = DIST / f"SHA256SUMS-v{version_text}.txt"
    prefix = f"dsh-theme-sandrone-{version_text}/"

    files = collect()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            bundle.write(path, prefix + path.relative_to(ROOT).as_posix())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sum_file.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"version: {version_text}")
    print(f"files:   {len(files)}")
    print(f"archive: {archive} ({archive.stat().st_size} bytes)")
    print(f"sha256:  {digest}")
    print(f"sums:    {sum_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
