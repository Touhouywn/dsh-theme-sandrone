"""06 发布库构建：usable 行 -> 07-release/clips/CN_<prts_idx>.wav + manifest.json。

P2（素材授权、抽听签字、对外发布）不在这里做；本脚本只到 build + smoke。
旧版先备份到 backup/release-pre-<ts>/，smoke 失败自动回滚。
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, LOGS, ROOT, SLICES, TAGGED, max_volume, read_json, write_json  # noqa: E402

USABLE_SCORE = 0.55
RELEASE = ROOT / "07-release"
BACKUP = ROOT / "backup"


def rows() -> list[dict]:
    with open(TAGGED / "aligned.tsv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(key: str) -> dict:
    al = rows()
    cross = {i["id"]: i for i in read_json(ASR / f"{key}.cross.json")["items"]}
    index = {c["id"]: c for c in read_json(SLICES / key / "clips" / "index.json")["clips"]}

    def usable_row(r: dict) -> bool:
        if (r.get("note") or "").startswith("pro-accepted"):
            return True
        try:
            return float(r.get("asr_score") or "") >= USABLE_SCORE
        except ValueError:
            return False

    usable = [r for r in al if r["status"] == "ok" and r["clip_id"] and usable_row(r)]

    if RELEASE.exists():
        BACKUP.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = BACKUP / f"release-pre-{stamp}"
        shutil.move(str(RELEASE), dest)
        print(f"备份旧发布库 -> {dest}")

    clips_dir = RELEASE / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    seen = set()
    for r in usable:
        idx = int(r["prts_idx"])
        name = f"CN_{idx:03d}.wav"
        clip = index[r["clip_id"]]
        src = SLICES / key / "clips" / clip["file"]
        dst = clips_dir / name
        shutil.copyfile(src, dst)
        entry = {**r, "releaseFile": f"clips/{name}",
                 "sha256": sha256(dst), "bytes": dst.stat().st_size,
                 "asrScore": (float(r["asr_score"])
                              if str(r["asr_score"]).replace(".", "", 1).isdigit()
                              else (r["asr_score"] or "n/a")),
                 "whisper": cross[r["clip_id"]]["whisperRaw"]}
        manifest.append(entry)
        if name in seen:
            raise SystemExit(f"STOP：命名重复 {name}")
        seen.add(name)

    payload = {"sourceKey": key, "builtAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "usable": len(manifest), "items": manifest}
    write_json(RELEASE / "manifest.json", payload)
    return payload


def smoke(payload: dict) -> list[dict]:
    clips_dir = RELEASE / "clips"
    files = sorted(p.name for p in clips_dir.glob("CN_*.wav"))
    checks = []
    checks.append({"name": "count", "spec": f"= {payload['usable']}",
                   "actual": len(files), "ok": len(files) == payload["usable"]})
    bad_peak = []
    for it in payload["items"]:
        f = RELEASE / it["releaseFile"]
        if not f.exists():
            bad_peak.append((it["releaseFile"], "missing"))
            continue
        pk = max_volume(f, LOGS / "_release-smoke.log")
        if pk is None or pk <= -60:
            bad_peak.append((it["releaseFile"], pk))
    checks.append({"name": "files+peak", "spec": "存在且 max_volume > -60 dB",
                   "actual": f"{len(bad_peak)} 失败", "ok": not bad_peak})
    man = read_json(RELEASE / "manifest.json")
    ids = [int(i["prts_idx"]) for i in man["items"]]
    checks.append({"name": "manifest-parse", "spec": "可解析且 prts_idx 无重复",
                   "actual": f"{len(ids)} 条 / 重复 {len(ids) - len(set(ids))}",
                   "ok": len(ids) == len(set(ids))})
    return checks


def main(argv: list[str]) -> int:
    key = argv[0] if argv else "youngbranch"
    payload = build(key)
    checks = smoke(payload)
    for c in checks:
        print(f"  smoke {c['name']:<12} {'ok ' if c['ok'] else 'FAIL'} {c['actual']}")
    ok = all(c["ok"] for c in checks)
    if not ok and (BACKUP.exists()):
        cands = sorted(BACKUP.glob("release-pre-*"))
        if cands:
            shutil.rmtree(RELEASE, ignore_errors=True)
            shutil.move(str(cands[-1]), str(RELEASE))
            print(f"smoke 失败，已回滚 {cands[-1].name}")
    print(f"[{key}] 发布库 {payload['usable']} 条 -> {RELEASE}；P2 签字/发布未做")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
