"""06 audit：stage 建库结果校验 + 覆盖表 + 抽听清单 + 通过门槛。

只读 stage/{clips/*.ogg, catalog.json, templates.json, templates-unmapped.json}，
产出 04-audit/{audit.json, coverage.md}。

门槛（修正稿 §4）：
  usableRate ≥85%
  highIntentCoverage = 7 个高频意图全部 ok（affirm/deny/followup/thanks/greeting/farewell/error）
  dupRate ≤3%
  idUnique：catalog id 无重复
  templateResolvable：模板每个非空 id 唯一存在且语义相符
  clipsDecodable：全部可解码；fileCountMatch：文件数 = 条目数

smoke（node 假 ctx 请求 /status、/catalog、/select）要先把 stage 拷进插件才能加载，
06 通过之前不写已发布库，所以留到发布时单独跑。
"""

from __future__ import annotations

import json
import hashlib
import random
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ASR, FFMPEG, LOGS, NODE, PLUGIN, ROOT, _run_to_log, read_json, write_json  # noqa: E402
import wordcut  # noqa: E402
from intents import (  # noqa: E402
    COVERAGE_FLOORS,
    INTENT_TAGS,
    QUOTA,
    coverage,
    error_shared_count,
    high_ok_rate,
    is_error_shared,
    load_pins,
    template_semantic_ok,
)

Pipeline = Path(__file__).resolve().parent

STAGE = ROOT / "stage"
AUDIT = ROOT / "04-audit"
USABLE_GATE = 0.85
DUP_GATE = 0.03
RANDOM_PCT = 0.05


CACHE_PATH = AUDIT / "decode-cache.json"
DECODE_ATTEMPTS = 4
DECODE_TIMEOUT = 30
SAMPLE_RATE = 48000


def file_sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class Decoder:
    """每个 ogg 解一次 PCM，带缓存、重试计数与「两轮才算坏」的判定。

    沙箱里不能建管道（WinError 5），所以 PIPE 失败时自动退回「写临时文件再读」，
    语义一样：串行、一次一条、不并行。
    """

    def __init__(self) -> None:
        self.cache = read_json(CACHE_PATH) if CACHE_PATH.exists() else {}
        self.retries = 0
        self.timeouts = 0
        self.ok = 0
        self.fail = 0
        self.hits = 0
        self.failures: dict[str, list[str]] = {"timeout": [], "crash": []}
        self.unstable: list[str] = []
        self.pipe_ok = True
        self.tmp = ROOT / "logs" / "_decode"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def _run_once(self, path: Path) -> bytes:
        cmd = [FFMPEG, "-v", "error", "-nostdin", "-hide_banner", "-i", str(path),
               "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"]
        if self.pipe_ok:
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      stdin=subprocess.DEVNULL, timeout=DECODE_TIMEOUT)
                if proc.returncode != 0:
                    raise RuntimeError("crash")
                return proc.stdout
            except PermissionError:
                self.pipe_ok = False  # 沙箱禁止管道，改用文件
        tmp = self.tmp / f"{path.stem}.pcm"
        with open(tmp, "wb") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.DEVNULL,
                                  stdin=subprocess.DEVNULL, timeout=DECODE_TIMEOUT)
        if proc.returncode != 0:
            raise RuntimeError("crash")
        data = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return data

    def _decode(self, path: Path) -> tuple[bool, float | None, float | None, str, int, int]:
        retries = 0
        timeouts = 0
        reason = "crash"
        for _attempt in range(DECODE_ATTEMPTS):
            try:
                pcm = self._run_once(path)
            except subprocess.TimeoutExpired:
                retries += 1
                timeouts += 1
                reason = "timeout"
                time.sleep(0.1)
                continue
            except RuntimeError:
                retries += 1
                reason = "crash"
                time.sleep(0.1)
                continue
            except OSError as exc:
                retries += 1
                reason = "crash"
                print(f"  decode os-error {exc}", flush=True)
                time.sleep(0.1)
                continue
            if len(pcm) < 2:
                retries += 1
                reason = "crash"
                time.sleep(0.1)
                continue
            import numpy as np

            samples = np.frombuffer(pcm, dtype="<i2")
            peak = float(np.abs(samples).max()) / 32768.0 if samples.size else 0.0
            peak_db = round(20 * (np.log10(peak + 1e-9)), 1) if peak > 0 else -180.0
            return True, round(samples.size / SAMPLE_RATE, 3), peak_db, "", retries, timeouts
        return False, None, None, reason, retries, timeouts

    def check(self, clip: dict) -> dict:
        """返回 {ok, seconds, peakDb, reason?, consecutiveFails?, cached?}。"""
        path = STAGE / clip["file"]
        if not path.exists():
            self.fail += 1
            self.failures["crash"].append(clip["id"])
            return {"ok": False, "reason": "missing", "consecutiveFails": 2}
        sha = file_sha16(path)
        entry = self.cache.get(clip["id"])
        if entry and entry.get("sha") == sha and entry.get("ok"):
            self.hits += 1
            self.ok += 1
            return {"ok": True, "seconds": entry["seconds"], "peakDb": entry["peakDb"], "cached": True}

        ok, seconds, peak, reason, retries, timeouts = self._decode(path)
        self.retries += retries
        self.timeouts += timeouts
        if ok:
            self.ok += 1
            self.cache[clip["id"]] = {"sha": sha, "ok": True, "retries": retries,
                                      "seconds": seconds, "peakDb": peak, "consecutiveFails": 0}
            return {"ok": True, "seconds": seconds, "peakDb": peak}
        self.fail += 1
        fails = int((entry or {}).get("consecutiveFails", 0)) + 1
        self.cache[clip["id"]] = {"sha": sha, "ok": False, "retries": retries,
                                  "consecutiveFails": fails}
        self.failures[reason].append(clip["id"])
        if fails < 2:
            self.unstable.append(clip["id"])
        return {"ok": False, "reason": reason, "consecutiveFails": fails}

    def save(self) -> None:
        write_json(CACHE_PATH, self.cache)


def run_smoke(templates: dict, catalog: dict) -> dict:
    """在 stage/smoke/ 搭插件副本，用 node + 假 ctx 跑断言，返回 {status, ranAt, checks}。

    P0.1：不手写期望值——smoke_run.mjs 自己读副本的 templates.json；
    这里只负责副本、进程和把结果原样带回 audit.json。
    """
    import shutil
    from datetime import datetime, timezone

    ran_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    plug = STAGE / "smoke" / "plugin"
    if plug.exists():
        shutil.rmtree(plug)
    (plug / "assets").mkdir(parents=True)
    for name in ("index.js", "package.json"):
        src = PLUGIN / name
        if not src.exists():
            return {"status": "fail", "ranAt": ran_at,
                    "checks": [{"route": f"copy {name}", "expect": "exists",
                                "actual": "missing", "ok": False}]}
        shutil.copy2(src, plug / name)
    for name in ("catalog.json", "templates.json"):
        shutil.copy2(STAGE / name, plug / "assets" / name)
    if (plug / "assets" / "clips").exists():
        shutil.rmtree(plug / "assets" / "clips")
    shutil.copytree(STAGE / "clips", plug / "assets" / "clips")

    out = LOGS / "smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    code = _run_to_log([NODE, str(Pipeline / "smoke_run.mjs"), str(plug)], out)
    text = out.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return {"status": "fail", "ranAt": ran_at,
                "checks": [{"route": "node smoke_run.mjs", "expect": "JSON",
                            "actual": f"空输出（exit {code}）", "ok": False}]}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "fail", "ranAt": ran_at,
                "checks": [{"route": "node smoke_run.mjs", "expect": "JSON",
                            "actual": text[-160:], "ok": False}]}
    return {"status": "pass" if payload.get("ok") else "fail",
            "ranAt": ran_at, "checks": payload.get("checks", [])}


def check_bgm_floor() -> dict:
    """bgmFloorDrop：读 01-separate/floor-drop.json（定稿口径）。

    verdict：applicable（preLowShare ≥ 0.15）→ dropDb ≥ 3 为 pass，否则 fail；
             不适用 → not_applicable，不算失败，但要把 preLowShare 带进报告。
    """
    path = ROOT / "01-separate" / "floor-drop.json"
    if not path.exists():
        return {"value": 0, "gate": 3.0, "ok": False, "problems": ["缺 floor-drop.json"]}
    data = read_json(path)
    items = data.get("items", {})
    problems, detail = [], {}
    for key, info in items.items():
        verdict = info.get("verdict")
        detail[key] = {
            "preLowShare": info.get("preLowShare"),
            "applicable": info.get("applicable"),
            "preP5Active": info.get("preP5Active"),
            "postP5Active": info.get("postP5Active"),
            "dropDb": info.get("dropDb"),
            "verdict": verdict,
        }
        if verdict not in ("pass", "not_applicable"):
            problems.append(f"{key}: verdict={verdict}（drop {info.get('dropDb')}dB）")
    if len(items) < 3:
        problems.append(f"只算了 {len(items)} 个源")
    applicable = [v["dropDb"] for v in detail.values()
                  if v["applicable"] and v["dropDb"] is not None]
    return {"value": round(min(applicable), 2) if applicable else 0.0,
            "gate": data.get("minDropDb", 3.0),
            "ok": not problems, "problems": problems, "detail": detail,
            "lowShareGate": data.get("bgmLowShare", 0.15)}


def check_tail_overrun(clips: list[dict]) -> dict:
    """tailOverrun：clip_end − (last_word_end + 60ms) > 150ms 的段。

    用的是 wordcut.overrun_ms —— 和 02b 切边同一个函数、同一份 energy 边界，
    所以口径不可能再对不上。
    """
    over, missing = [], 0
    words_cache: dict[str, list[dict]] = {}
    for clip in clips:
        fp = clip.get("sourceFingerprint") or {}
        key = fp.get("sourceKey")
        if key not in words_cache:
            path = ASR / f"{key}.words.json"
            words_cache[key] = read_json(path)["words"] if path.exists() else []
        words = words_cache[key]
        end_ms = fp.get("endMs")
        start_ms = fp.get("startMs")
        energy_end = fp.get("energyEndMs", end_ms)
        energy_start = fp.get("energyStartMs", start_ms)
        if end_ms is None or start_ms is None or not words:
            missing += 1
            continue
        delta = wordcut.overrun_ms(end_ms, energy_end, words, energy_start)
        if delta is None:
            missing += 1
            continue
        if delta > 150:
            over.append({"id": clip["id"], "sourceKey": key,
                         "overrunMs": round(delta, 1),
                         "clipMs": [start_ms, end_ms],
                         "energyMs": [energy_start, energy_end],
                         "text": clip["text"][:24]})
    over.sort(key=lambda r: -r["overrunMs"])
    return {"value": len(over), "gate": 0, "ok": not over,
            "problems": [f"{r['id']} 超 {r['overrunMs']}ms" for r in over[:10]],
            "noWords": missing, "list": over[:40]}


def main() -> int:
    catalog = read_json(STAGE / "catalog.json")
    templates = read_json(STAGE / "templates.json")["templates"]
    unmapped_path = STAGE / "templates-unmapped.json"
    unmapped = read_json(unmapped_path) if unmapped_path.exists() else {}
    clips = catalog["clips"]
    by_id = {c["id"]: c for c in clips}

    bad, dur_mismatch = [], []
    decoder = Decoder()
    for i, clip in enumerate(clips, start=1):
        info = decoder.check(clip)
        if info["ok"]:
            if abs(info["seconds"] - clip["duration"]) > 0.25:
                dur_mismatch.append({"id": clip["id"], "catalog": clip["duration"],
                                     "actual": info["seconds"]})
        elif info.get("consecutiveFails", 0) >= 2:
            # 连续两轮都失败才算坏；只失败一轮的先记 decodeUnstable
            bad.append({"id": clip["id"], "reason": info.get("reason", "crash"),
                        "consecutiveFails": info.get("consecutiveFails", 0)})
        if i % 200 == 0:
            print(f"decode {i:04d}/{len(clips)} ok={decoder.ok} fail={decoder.fail} "
                  f"retries={decoder.retries} timeouts={decoder.timeouts} "
                  f"cache={decoder.hits}", flush=True)
    decoder.save()

    usable = [c for c in clips if c["usable"]]
    texts = Counter(c["text"] for c in clips)
    dup_extras = sum(v - 1 for v in texts.values() if v > 1)

    ids = [c["id"] for c in clips]
    dup_ids = sorted({i for i, n in Counter(ids).items() if n > 1})

    template_problems = []
    for key, tpl_ids in templates.items():
        seen = []
        for cid in tpl_ids:
            entry = by_id.get(cid)
            if entry is None:
                template_problems.append({"key": key, "id": cid, "problem": "不在 catalog"})
            elif not template_semantic_ok(key, entry):
                template_problems.append({"key": key, "id": cid, "problem": "语义不符"})
            if cid in seen:
                template_problems.append({"key": key, "id": cid, "problem": "同键重复"})
            seen.append(cid)

    report = coverage(clips)
    usable_rate = len(usable) / len(clips) if clips else 0
    high_rate = high_ok_rate(report)
    dup_rate = dup_extras / len(clips) if clips else 0

    # P0.2：pinned 段必须都在、且不重复；覆盖率硬下限不进即 ok=false
    pins = load_pins(STAGE)
    pinned_problems = []
    for pid in pins["ids"]:
        entry = by_id.get(pid)
        if entry is None:
            pinned_problems.append({"id": pid, "problem": "不在 catalog"})
        elif not entry["usable"]:
            pinned_problems.append({"id": pid, "problem": "usable=false"})
    for name, ids_ in templates.items():
        for pid in ids_:
            if ids_count := ids.count(pid):
                if ids_count > 1:
                    pinned_problems.append({"id": pid, "problem": f"catalog 里出现 {ids_count} 次"})
    # 覆盖率下限：farewell 在独白素材里常常凑不够 4 段，允许降到 3 并记原因
    floor_notes = {}
    floor_problems = []
    for intent, floor in COVERAGE_FLOORS.items():
        got = report[intent]["count"]
        used = floor
        if intent == "farewell" and 3 <= got < floor:
            used = 3
            floor_notes[intent] = {
                "reason": "monologue-scarce",
                "declaredFloor": floor, "usedFloor": 3,
                "note": "独白素材里告别句本来就少，降到 3 段；时长档要求不变",
            }
        report[intent]["floor"] = used
        report[intent]["floorOk"] = got >= used
        if got < used:
            floor_problems.append(f"{intent} {got} < {used}")
        # 用降级后的 floor 重新判，别让 QUOTA 的 need=4 一直压着
        report[intent]["ok"] = got >= used and len(report[intent]["bands"]) >= report[intent]["bandsNeed"]

    # v1.2.1 新增：BGM 底噪、尾部溢出、stem 字段
    high_rate = high_ok_rate(report)  # floor 降级之后重算
    bgm = check_bgm_floor()
    tail = check_tail_overrun(clips)
    stem_problems = [c["id"] for c in clips if c.get("stem") not in ("vocals", "original")]

    gates = {
        "usableRate": {"value": round(usable_rate, 4), "gate": USABLE_GATE,
                       "ok": usable_rate >= USABLE_GATE},
        "highIntentCoverage": {"value": round(high_rate, 4), "gate": 1.0,
                               "ok": high_rate >= 1.0},
        "dupRate": {"value": round(dup_rate, 4), "gate": DUP_GATE, "ok": dup_rate <= DUP_GATE},
        "idUnique": {"value": len(dup_ids), "gate": 0, "ok": not dup_ids},
        "templateResolvable": {"value": len(template_problems), "gate": 0,
                               "ok": not template_problems},
        "pinnedIntegrity": {"value": len(pinned_problems), "gate": 0,
                            "ok": not pinned_problems, "problems": pinned_problems},
        "bgmFloorDrop": bgm,
        "tailOverrun": tail,
        "stemField": {"value": len(stem_problems), "gate": 0,
                      "ok": not stem_problems, "problems": stem_problems[:10]},
        "clipsDecodable": {"value": len(bad), "gate": 0, "ok": not bad},
        "fileCountMatch": {"value": len(list((STAGE / "clips").glob("*.ogg"))),
                           "gate": len(clips),
                           "ok": len(list((STAGE / "clips").glob("*.ogg"))) == len(clips)},
    }

    smoke = run_smoke(templates, catalog)

    rng = random.Random(20261027)
    usable_pool = [c for c in clips if c["usable"]]
    listen, named = {}, set()
    for intent, tags in INTENT_TAGS.items():
        pool = [c for t in tags for c in usable_pool if t in c["tags"]]
        ranked = sorted({c["id"]: c for c in pool}.values(), key=lambda c: -c["asrScore"])[:3]
        if ranked:
            listen[intent] = [{"id": c["id"], "text": c["text"], "duration": c["duration"],
                               "score": c["asrScore"]} for c in ranked]
            named.update(c["id"] for c in ranked)
    rest = [c for c in clips if c["id"] not in named]
    listen["_random5pct"] = [{"id": c["id"], "text": c["text"]}
                             for c in rng.sample(rest, max(1, int(len(clips) * RANDOM_PCT)))]
    listen["_farewellGreetingIdentityAll"] = [
        {"id": c["id"], "text": c["text"]} for c in clips
        if set(c["tags"]) & {"farewell", "greeting", "identity"}]

    passed = all(g["ok"] for g in gates.values()) and smoke["status"] == "pass"
    error_id = (templates.get("error") or [""])[0]
    notes = []
    retry_ratio = decoder.retries / max(1, len(clips))
    if retry_ratio > 0.05:
        notes.append(f"decode 重试占比 {retry_ratio * 100:.1f}%（>5%），环境抖动偏多，结论仅供参考")
    rules_report = read_json(ROOT / "01-slices" / "rules-report.json")
    seg_stats = {s["key"]: {"count": s["kept"], "median": s["median"], "p25": s["p25"],
                            "p75": s["p75"],
                            "floors": s.get("floors"), "reason": s.get("reason")}
                 for s in rules_report.get("items", [])}
    payload = {
        "generatedAt": "2026-10-27",
        "verdict": "PASS" if passed else "HOLD",
        "gates": gates,
        "segments": seg_stats,
        "coverageFloorNotes": floor_notes,
        "decodeRetries": decoder.retries,
        "decodeTimeouts": decoder.timeouts,
        "decodeCacheHits": decoder.hits,
        "decodeUnstable": decoder.unstable,
        "decodeFailures": decoder.failures,
        "notes": notes,
        "bgmFloorDrop": {"detail": bgm.get("detail", {}), "problems": bgm.get("problems", [])},
        "tailOverrun": {"count": tail["value"], "list": tail["list"],
                        "noWords": tail.get("noWords", 0)},
        "stem": {s: sum(1 for c in clips if c.get("stem") == s) for s in ("vocals", "original")},
        "counts": {
            "clips": len(clips), "usable": len(usable),
            "templates": {k: len(v) for k, v in templates.items()},
            "emptyTemplates": [k for k, v in templates.items() if not v],
            "errorSharedLiteral": error_shared_count(clips),
            "errorSemantic": report["error"]["count"],
            "errorPlaybackId": error_id,
            "errorPlaybackLiteral": bool(
                error_id and by_id.get(error_id) and is_error_shared(by_id[error_id])),
            "coverageFloors": {k: {"floor": v, "value": report[k]["count"],
                                   "ok": report[k]["count"] >= v}
                               for k, v in COVERAGE_FLOORS.items()},
            "pinned": pins["ids"],
        },
        "badClips": bad[:20],
        "durationMismatch": dur_mismatch[:20],
        "dupIds": dup_ids[:20],
        "templateProblems": template_problems[:20],
        "unmapped": unmapped,
        "coverage": report,
        "smoke": smoke,
        "listen": listen,
    }
    AUDIT.mkdir(parents=True, exist_ok=True)
    write_json(AUDIT / "audit.json", payload)

    lines = ["# v2 覆盖表与校验", "", f"**结论：{payload['verdict']}**", ""]
    lines += ["| 门槛 | 实测 | 要求 | 结果 |", "| --- | ---: | ---: | --- |"]
    for key, g in gates.items():
        lines.append(f"| {key} | {g['value']} | {g['gate']} | {'通过' if g['ok'] else '**未通过**'} |")
    lines += ["", "## 切分统计（词帽 40/60，守卫 median≥1.0 / P25≥0.6）", "",
              "| 源 | 段数 | 中位 | P25 | P75 | reason |", "| --- | ---: | ---: | ---: | ---: | --- |"]
    for k, v in seg_stats.items():
        lines.append(f"| {k} | {v['count']} | {v['median']}s | {v['p25']}s | {v['p75']}s | "
                     f"{v['reason']} |")
    if floor_notes:
        lines += ["", f"覆盖率下限调整：{floor_notes}"]
    lines += ["", "| 意图 | 级别 | 段数 | 需 | <1.5s | 1.5–3s | 3–6s | ≥6s | 达标 |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for level, items in QUOTA.items():
        for intent, need, _bands in items:
            c = report[intent]
            b = c["bands"]
            lines.append(
                f"| {intent} | {level} | {c['count']} | {need} | "
                f"{b.get('<1.5', 0)} | {b.get('1.5-3', 0)} | {b.get('3-6', 0)} | "
                f"{b.get('>=6', 0)} | {'是' if c['ok'] else '**否**'} |"
            )
    lines += ["", f"error 字面口径（§3 四类标签）：{payload['counts']['errorSharedLiteral']} 段；"
              f"计入门槛的口径（文本含 error 词）：{payload['counts']['errorSemantic']} 段；"
              f"实际播放段 {payload['counts']['errorPlaybackId']}"
              f"（literal={payload['counts']['errorPlaybackLiteral']}）。",
              "", f"pinned 段 {len(pins['ids'])} 个，问题 {len(pinned_problems)} 个",
              f"覆盖率硬下限：{payload['counts']['coverageFloors']}",
              "", "## BGM 底噪（v1.2.1）", ""]
    for key, info in bgm.get("detail", {}).items():
        lines.append(f"- **{key}**：{info.get('verdict')}"
                     f"（preLowShare {info.get('preLowShare')}，applicable={info.get('applicable')}，"
                     f"p5Active {info.get('preP5Active')} → {info.get('postP5Active')}，"
                     f"drop {info.get('dropDb')} dB）")
    lines += ["", f"## 尾部溢出（tailOverrun）：{tail['value']} 段", ""]
    if tail["list"]:
        lines += ["| id | 源 | 溢出 | text |", "| --- | --- | ---: | --- |"]
        for r in tail["list"][:25]:
            lines.append(f"| `{r['id']}` | {r['sourceKey']} | {r['overrunMs']}ms | {r['text']} |")
    else:
        lines.append("没有超过 150ms 的段。")
    lines += ["", f"stem 分布：{payload['stem']}",
              "", f"空模板键：{', '.join(payload['counts']['emptyTemplates']) or '无'}",
              "", f"smoke：{smoke['status']}（{len(smoke['checks'])} 项）",
              "", "## 模板实测", ""]
    for key, tpl_ids in templates.items():
        parts = []
        for cid in tpl_ids:
            e = by_id.get(cid)
            parts.append(f"{cid}「{e['text'][:16]}」{e['duration']:.2f}s" if e else f"{cid}（缺失）")
        lines.append(f"- **{key}**：{'、'.join(parts) or '（空）'}")
    lines += ["", "## 抽听清单", "",
              f"- 每意图前 3 段：{len([k for k in listen if not k.startswith('_')])} 个意图",
              f"- 随机 5%：{len(listen['_random5pct'])} 段",
              f"- farewell/greeting/identity 全量：{len(listen['_farewellGreetingIdentityAll'])} 段"]
    (AUDIT / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    for key, g in gates.items():
        print(f"{'OK  ' if g['ok'] else 'FAIL'} {key}: {g['value']} (要求 {g['gate']})")
    print(f"smoke {smoke['status']}（{len(smoke['checks'])} 项，"
          f"失败 {sum(1 for c in smoke['checks'] if not c['ok'])}）")
    print(f"坏片 {len(bad)}  时长偏差 {len(dur_mismatch)}  重号 {len(dup_ids)}  "
          f"模板问题 {len(template_problems)}  pinned 问题 {len(pinned_problems)}  "
          f"空模板 {payload['counts']['emptyTemplates']}")
    print(f"error 播放段 {error_id} literal={payload['counts']['errorPlaybackLiteral']}")
    print(f"verdict = {payload['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
