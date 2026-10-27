"""把 A/B 抽听包做成一个能点的页面（音频内嵌，双击即听）。

读 01-separate/ab-listen/index.json 与同名 ogg，
写 01-separate/ab-listen/listen.html。
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, read_json  # noqa: E402

AB = ROOT / "01-separate" / "ab-listen"
TITLES = {
    "v1-training": "v1-training · BV1C5s6zaE3P",
    "v2-story62": "v2-story62 · BV1wt2jBwE4p",
    "v3-fullvoice": "v3-fullvoice · BV1fQzSBMEbs",
}


def data_uri(path: Path) -> str:
    return "data:audio/ogg;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> int:
    index = read_json(AB / "index.json")
    blocks, total = [], 0
    for key, rows in index["items"].items():
        if not rows:
            continue
        trs = []
        for r in rows:
            o = AB / key / r["original"] if r.get("original") else None
            v = AB / key / r["vocals"] if r.get("vocals") else None
            if not o or not v or not o.exists() or not v.exists():
                continue
            total += 1
            trs.append(
                f'<tr>'
                f'<td class="num">{r["index"]:02d}</td>'
                f'<td class="num">{r["startMs"]}–{r["endMs"]}ms</td>'
                f'<td class="num">{r["duration"]:.2f}s</td>'
                f'<td class="num share">{r["preLowShare"]:.3f}</td>'
                f'<td><button class="play" data-ab="o" data-a="{data_uri(o)}" data-b="{data_uri(v)}">原轨</button></td>'
                f'<td><button class="play" data-ab="v" data-a="{data_uri(o)}" data-b="{data_uri(v)}">人声</button></td>'
                f'<td><button class="ab" data-a="{data_uri(o)}" data-b="{data_uri(v)}">先原轨再人声</button></td>'
                f'</tr>'
            )
        blocks.append(
            f'<section><h2>{TITLES.get(key, key)} <small>{len(trs)} 段</small></h2>'
            f'<table><thead><tr><th>#</th><th>段</th><th>时长</th>'
            f'<th>pre 低频占比</th><th></th><th></th><th></th></tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></section>'
        )

    html = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>A/B 抽听</title>
<style>
:root {{ color-scheme: dark }}
body {{ background:#080b16; color:#e9eeff; font:14px/1.7 system-ui,"Segoe UI",sans-serif; margin:0; padding:28px 32px 80px }}
h1 {{ font-size:20px; margin:0 0 6px }}
h2 {{ font-size:15px; color:#cbb6ee; margin:30px 0 6px }}
h2 small {{ color:#7e88a8; font-weight:400 }}
p.hint {{ color:#7e88a8; font-size:12px; margin:0 0 14px; max-width:900px }}
table {{ border-collapse:collapse; max-width:1000px }}
th,td {{ padding:6px 10px; border-bottom:1px solid #1a2138; text-align:left }}
th {{ color:#8b96b8; font-weight:500; font-size:12px }}
td.num {{ font-variant-numeric:tabular-nums; color:#a9b3cc }}
td.share {{ color:#f0b6c8 }}
button {{ background:#1b2440; color:#e9eeff; border:1px solid #2b3a63; border-radius:8px; padding:3px 12px; cursor:pointer; font-size:13px }}
button:hover {{ border-color:#cbb6ee }}
tr.playing td {{ background:#141c33 }}
#bar {{ position:sticky; top:0; background:#080b16f2; padding:8px 0; border-bottom:1px solid #1a2138; margin-bottom:8px }}
#now {{ color:#9fd8f5; font-size:13px; margin-left:10px }}
</style></head><body>
<h1>A/B 抽听 · 原轨 vs 人声分离</h1>
<p class="hint">同一段的两次切边界完全一致，只换音源：先听「原轨」再听「人声」，该留下的留下、该消失的消失。
排序按「安静帧低频占比」降序——BGM 在安静处最藏不住，3 个源共 {total} 段。</p>
<div id="bar"><button id="stop">停</button><span id="now"></span></div>
{''.join(blocks)}
<audio id="player"></audio>
<script>
const player = document.getElementById('player')
const now = document.getElementById('now')
let queue = []

function clearMarks() {{ document.querySelectorAll('tr.playing').forEach((r) => r.classList.remove('playing')) }}
function play(src, row, label) {{
  clearMarks()
  if (row) row.classList.add('playing')
  now.textContent = label || ''
  player.src = src
  player.play()
}}
document.addEventListener('click', (e) => {{
  const btn = e.target.closest('button')
  if (!btn) return
  if (btn.id === 'stop') {{ queue = []; player.pause(); clearMarks(); now.textContent = ''; return }}
  const row = btn.closest('tr')
  if (btn.dataset.ab) {{
    queue = []
    play(btn.dataset[btn.dataset.ab], row, btn.textContent + ' · ' + (row ? row.children[1].textContent : ''))
  }} else if (btn.classList.contains('ab')) {{
    queue = [{{ src: btn.dataset.b, row, label: '人声' }}]
    play(btn.dataset.a, row, '原轨 → 接着人声')
  }}
}})
player.addEventListener('ended', () => {{
  if (queue.length) {{ const n = queue.shift(); play(n.src, n.row, n.label) }}
  else {{ clearMarks(); now.textContent = '' }}
}})
</script>
</body></html>"""

    out = AB / "listen.html"
    out.write_text(html, encoding="utf-8")
    print(f"写了 {out}（{total} 段，{out.stat().st_size / 1e6:.2f} MB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
