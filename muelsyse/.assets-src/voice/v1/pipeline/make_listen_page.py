"""把抽听清单做成一个能点的页面：每段音频内嵌成 data URI，双击就能听。

只读 publish/{clips,catalog.json} 与 04-audit/listen-triage.md 的指标（重算一遍更准），
产出 04-audit/listen.html —— 单个文件，不依赖服务器，直接双击打开。
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, read_json  # noqa: E402
from triage_listen import analyze, flags  # noqa: E402

PUBLISH = ROOT / "publish"
AUDIT = ROOT / "04-audit"

SECTIONS = [
    ("模板段", "每键必听；code / fact 本该为空，走 L2 检索。"),
    ("意图 top3", "按 asrScore 降序取前三，看这个意图整体像不像。"),
    ("随机 5%", "盲听，找之前没注意到的毛病。"),
    ("greeting / farewell / identity 全量", "这三类最容易撞到别人，全听。"),
]


def parse_sections(path: Path) -> dict[str, list[str]]:
    """把 markdown 按 ## 段落切开，各自取 id（保序去重）。"""
    text = path.read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    for chunk in re.split(r"^## ", text, flags=re.M)[1:]:
        title = chunk.splitlines()[0].strip()
        ids = list(dict.fromkeys(re.findall(r"`(c\d{4})`", chunk)))
        if ids:
            out[title] = ids
    return out


def main() -> int:
    catalog = {c["id"]: c for c in read_json(PUBLISH / "catalog.json")["clips"]}
    sections = parse_sections(AUDIT / "listen-checklist.md")

    ids = []
    for v in sections.values():
        for cid in v:
            if cid not in ids:
                ids.append(cid)

    metrics = {}
    for cid in ids:
        path = PUBLISH / "clips" / f"{cid}.ogg"
        if not path.exists():
            continue
        info = analyze(path)
        if info is None:
            continue
        metrics[cid] = {**info, "flags": flags(info)}

    blocks = []
    total = 0
    for title, ids_ in sections.items():
        rows = [c for c in ids_ if c in metrics]
        if not rows:
            continue
        body = []
        for cid in rows:
            c = catalog[cid]
            info = metrics[cid]
            audio = base64.b64encode((PUBLISH / "clips" / f"{cid}.ogg").read_bytes()).decode()
            total += 1
            flag = "、".join(info["flags"]) or "—"
            body.append(
                f'<tr data-id="{cid}">'
                f'<td class="id">{cid}</td>'
                f'<td class="txt">{c["text"]}</td>'
                f'<td class="num">{c["duration"]:.2f}s</td>'
                f'<td class="num">{c["asrScore"]:.3f}</td>'
                f'<td class="num">{info["peakDb"]}</td>'
                f'<td class="num">{info["headSilenceMs"]}/{info["tailSilenceMs"]}ms</td>'
                f'<td class="flag">{flag}</td>'
                f'<td><button class="play" data-src="data:audio/ogg;base64,{audio}">听</button></td>'
                f"</tr>"
            )
        blocks.append(
            f'<section><h2>{title} <small>{len(rows)} 段</small></h2>'
            f'<p class="hint">{SECTIONS[[s[0] for s in SECTIONS].index(title)][1] if title in [s[0] for s in SECTIONS] else ""}</p>'
            f'<table><thead><tr><th>id</th><th>text</th><th>时长</th><th>asr</th>'
            f'<th>peak</th><th>头/尾静音</th><th>标记</th><th></th></tr></thead>'
            f"<tbody>{''.join(body)}</tbody></table></section>"
        )

    html = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>v2 抽听</title>
<style>
:root {{ color-scheme: dark }}
body {{ background:#080b16; color:#e9eeff; font:14px/1.6 system-ui,"Segoe UI",sans-serif; margin:0; padding:28px 32px 80px }}
h1 {{ font-size:20px; font-weight:600; margin:0 0 6px }}
h2 {{ font-size:15px; font-weight:600; margin:34px 0 4px; color:#cbb6ee }}
h2 small {{ color:#7e88a8; font-weight:400 }}
.hint {{ color:#7e88a8; margin:0 0 10px; font-size:12px }}
table {{ border-collapse:collapse; width:100%; max-width:1180px }}
th,td {{ text-align:left; padding:6px 10px; border-bottom:1px solid #1a2138; vertical-align:middle }}
th {{ color:#8b96b8; font-weight:500; font-size:12px }}
td.id {{ font-family:ui-monospace,Consolas,monospace; color:#9fd8f5 }}
td.num {{ font-variant-numeric:tabular-nums; color:#a9b3cc }}
td.flag {{ color:#f0b6c8; font-size:12px }}
tr.playing {{ background:#141c33 }}
.play {{ background:#1b2440; color:#e9eeff; border:1px solid #2b3a63; border-radius:8px; padding:3px 12px; cursor:pointer }}
.play:hover {{ border-color:#cbb6ee }}
#bar {{ position:sticky; top:0; background:#080b16f2; padding:8px 0 10px; z-index:5; border-bottom:1px solid #1a2138 }}
#bar button {{ background:#1b2440; color:#e9eeff; border:1px solid #2b3a63; border-radius:8px; padding:5px 14px; cursor:pointer; margin-right:8px }}
#now {{ color:#9fd8f5; font-size:13px; margin-left:10px }}
</style></head><body>
<h1>v2 抽听 · 点「听」即播</h1>
<p class="hint">共 {total} 行（同一段可能出现在多个组里）。标记列是机器量的听感风险（切头 / 切尾 / 削波），只作提示，真判断靠耳朵。
头/尾静音是边界处低于该段自身底噪的静音长度，越小越可能切到字。</p>
<div id="bar"><button id="playAll">顺序播放本组</button><button id="stop">停</button><span id="now"></span></div>
{''.join(blocks)}
<audio id="player"></audio>
<script>
const player = document.getElementById('player')
const now = document.getElementById('now')
let queue = [], idx = 0, current = null

function mark(row) {{
  document.querySelectorAll('tr.playing').forEach((r) => r.classList.remove('playing'))
  if (row) row.classList.add('playing')
}}

function playOne(src, row) {{
  queue = []; current = row; mark(row)
  now.textContent = row ? (row.querySelector('.id').textContent + ' · ' + row.querySelector('.txt').textContent) : ''
  player.src = src
  player.play()
}}

document.addEventListener('click', (e) => {{
  const btn = e.target.closest('.play')
  if (btn) playOne(btn.dataset.src, btn.closest('tr'))
}})

player.addEventListener('ended', () => {{
  if (idx < queue.length) {{ const item = queue[idx++]; playOne(item.src, item.row) }}
  else {{ mark(null); now.textContent = '' }}
}})

document.getElementById('playAll').onclick = () => {{
  const rows = [...document.querySelectorAll('tbody tr')]
  queue = rows.map((row) => ({{ src: row.querySelector('.play').dataset.src, row }}))
  idx = 0
  if (queue.length) {{ const item = queue[idx++]; playOne(item.src, item.row) }}
}}

document.getElementById('stop').onclick = () => {{ queue = []; player.pause(); mark(null); now.textContent = '' }}
</script>
</body></html>"""

    out = AUDIT / "listen.html"
    out.write_text(html, encoding="utf-8")
    print(f"写了 {out}（{total} 段，{out.stat().st_size / 1e6:.2f} MB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
