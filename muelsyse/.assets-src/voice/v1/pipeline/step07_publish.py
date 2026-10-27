"""07 publish（P2）：过滤出发布集，再原子替换已发布库，失败即回滚。

用法：
  python step07_publish.py build     # v2/stage -> v2/publish，带断言
  python step07_publish.py replace   # 备份 assets -> 替换 -> 冒烟 -> 失败回滚

规则：
  发布集只留 usable=true 的行，clips 只拷这些行引用的文件。
  替换前把 assets/{clips,catalog.json,templates.json} 整个备份到 v2/backup/pre-v2-<时间戳>/。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import NODE, PLUGIN, ROOT, read_json, write_json  # noqa: E402

STAGE = ROOT / "stage"
PUBLISH = ROOT / "publish"
BACKUP_ROOT = ROOT / "backup"
ASSETS = PLUGIN / "assets"
PIPELINE = Path(__file__).resolve().parent
EXPECTED_ROWS = 1071
TEMPLATE_KEYS = 27
EMPTY_KEYS = {"code", "fact"}


def build() -> int:
    catalog = read_json(STAGE / "catalog.json")
    templates = read_json(STAGE / "templates.json")["templates"]
    clips = catalog["clips"]
    keep = [c for c in clips if c["usable"]]

    if PUBLISH.exists():
        shutil.rmtree(PUBLISH)
    (PUBLISH / "clips").mkdir(parents=True)
    for clip in keep:
        src = STAGE / "clips" / f"{clip['id']}.ogg"
        if not src.exists():
            raise SystemExit(f"STOP：缺文件 {src}")
        shutil.copy2(src, PUBLISH / "clips" / f"{clip['id']}.ogg")

    publish_ids = {c["id"] for c in keep}
    tpl = {k: [i for i in v if i in publish_ids] for k, v in templates.items()}
    write_json(PUBLISH / "catalog.json", {**catalog, "clips": keep})
    write_json(PUBLISH / "templates.json", {"version": 2, "templates": tpl})

    files = sorted(p.name for p in (PUBLISH / "clips").glob("*.ogg"))
    rows = len(keep)
    problems = []
    if rows != EXPECTED_ROWS or len(files) != EXPECTED_ROWS:
        problems.append(f"行数 {rows} / 文件数 {len(files)}，期望 {EXPECTED_ROWS}")
    if any(not c["usable"] for c in keep):
        problems.append("发布集里仍有 usable=false 的行")
    if len(publish_ids) != rows:
        problems.append("id 不唯一")
    if len(tpl) != TEMPLATE_KEYS:
        problems.append(f"模板键数 {len(tpl)}，期望 {TEMPLATE_KEYS}")
    for key in EMPTY_KEYS:
        if tpl.get(key):
            problems.append(f"{key} 应为空")
    for key, ids in tpl.items():
        if key in EMPTY_KEYS:
            continue
        if not ids:
            problems.append(f"{key} 为空")
        for cid in ids:
            if cid not in publish_ids:
                problems.append(f"{key} 指向了不在发布集的 {cid}")
        if len(ids) != len(set(ids)):
            problems.append(f"{key} 内部 id 重复")
    if problems:
        print("STOP：发布集断言未过")
        for p in problems:
            print("  -", p)
        return 1

    print(f"publish：{rows} 行 / {len(files)} 个 clip；usable 全 true；id 唯一；"
          f"模板 {len(tpl)} 键（code/fact 空）")
    return 0


def run_smoke(target: Path) -> tuple[bool, list[dict]]:
    out = ROOT / "logs" / "smoke-publish.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    code = subprocess.run(
        [NODE, str(PIPELINE / "smoke_run.mjs"), str(target)],
        stdout=open(out, "w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    ).returncode
    text = out.read_text(encoding="utf-8", errors="replace").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False, [{"route": "smoke", "expect": "JSON", "actual": text[-160:], "ok": False}]
    return bool(payload.get("ok")), payload.get("checks", [])


def replace() -> int:
    if not (PUBLISH / "catalog.json").exists():
        raise SystemExit("先跑 build")

    stamp = time.strftime("pre-v2-%Y%m%d-%H%M%S")
    backup = BACKUP_ROOT / stamp
    (backup / "clips").mkdir(parents=True, exist_ok=True)
    for name in ("catalog.json", "templates.json"):
        src = ASSETS / name
        if src.exists():
            shutil.copy2(src, backup / name)
    for old in (ASSETS / "clips").glob("*.ogg"):
        shutil.copy2(old, backup / "clips" / old.name)
    print(f"备份 -> {backup}（{len(list((backup / 'clips').glob('*.ogg')))} 个 clip）")

    checks: list[dict] = []
    try:
        for old in (ASSETS / "clips").glob("*.ogg"):
            old.unlink()
        for name in ("catalog.json", "templates.json"):
            (ASSETS / name).unlink(missing_ok=True)
        for src in (PUBLISH / "clips").glob("*.ogg"):
            shutil.copy2(src, ASSETS / "clips" / src.name)
        for name in ("catalog.json", "templates.json"):
            shutil.copy2(PUBLISH / name, ASSETS / name)

        ok, checks = run_smoke(PLUGIN)
        if not ok:
            raise RuntimeError("smoke 未过")
    except Exception as exc:  # noqa: BLE001 - 任何失败都回滚
        print(f"替换后校验失败：{exc}")
        for old in list((ASSETS / "clips").glob("*.ogg")):
            old.unlink()
        for src in (backup / "clips").glob("*.ogg"):
            shutil.copy2(src, ASSETS / "clips" / src.name)
        for name in ("catalog.json", "templates.json"):
            if (backup / name).exists():
                shutil.copy2(backup / name, ASSETS / name)
        print("已用备份回滚 -> STOP")
        for c in checks:
            if not c.get("ok"):
                print("  FAIL", c.get("route"), c.get("expect"), "=>", c.get("actual"))
        return 1

    assets_files = len(list((ASSETS / "clips").glob("*.ogg")))
    assets_rows = len(read_json(ASSETS / "catalog.json")["clips"])
    print(f"assets：{assets_files} 个 clip / catalog {assets_rows} 行")
    if assets_files != EXPECTED_ROWS or assets_rows != EXPECTED_ROWS:
        print("STOP：assets 数量与发布集不一致")
        return 1

    for c in checks:
        print(("OK  " if c["ok"] else "FAIL"), c["route"], "|", c["expect"], "=>", c["actual"])
    print(f"smoke {sum(1 for c in checks if c['ok'])}/{len(checks)} 通过")
    print(f"BACKUP={backup}")
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    raise SystemExit(build() if mode == "build" else replace())
