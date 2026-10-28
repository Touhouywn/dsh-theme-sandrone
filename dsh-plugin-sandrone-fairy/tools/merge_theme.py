"""把 fairy 的深蓝/紫 UI 并回合作者 1.0.0 发行包，做成可切换皮肤。

产出：default-workspace\\dsh-theme-sandrone-1.0.1\\（目录）+ 同名 zip。
- 默认 ui.skin = aurora：恢复 fairy 自己的 --dsw-* token 覆盖 + 深蓝/紫面板
- ui.skin = workshop：沿用主题的黑金皮肤（把 v1.0.0 那段 !important 覆盖收敛到 html.sdf-skin-workshop 下）
"""

import io
import os
import re
import shutil
import subprocess
import zipfile

WS = os.environ.get("SANDRONE_WS", "")
if not WS:
    raise SystemExit("未设置 SANDRONE_WS：请先 set SANDRONE_WS=<default-workspace 目录> 后再运行本脚本。")
SRC = os.path.join(WS, "ref-theme-1.0.0", "dsh-theme-sandrone-1.0.0")
OUT = os.path.join(WS, "dsh-theme-sandrone-1.0.1")
FAIRY = os.path.join(OUT, "dsh-plugin-sandrone-fairy")
CLIENT = os.path.join(FAIRY, "client.js")
INDEX = os.path.join(FAIRY, "index.js")

MARK = "/* ── integrated v1.0.0: black-and-gold palette ── */"


def read(p):
    return io.open(p, encoding="utf-8").read().replace("\r\n", "\n")


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def scope_css(block):
    # 先处理「单行规则」：.a { x: y } / .a, .b { x: y }
    def one_line(m):
        sel = m.group(1).strip()
        if sel.startswith("@") or sel.startswith("/*"):
            return m.group(0)
        parts = [p.strip() for p in sel.split(",") if p.strip()]
        return ", ".join("html.sdf-skin-workshop " + p for p in parts) + " {" + m.group(2) + "}"
    block = re.sub(r"(?m)^([^{}\n]+?)\s*\{([^{}]*)\}\s*$", one_line, block)

    out, in_rule = [], False
    for line in block.split("\n"):
        stripped = line.strip()
        if stripped.endswith("{") and not stripped.startswith("@") and not stripped.startswith("/*"):
            sel = stripped[:-1].strip()
            parts = [p.strip() for p in sel.split(",") if p.strip()]
            scoped = ", ".join("html.sdf-skin-workshop " + p for p in parts)
            out.append(scoped + " {")
            in_rule = True
        else:
            out.append(line)
        if stripped == "}" and in_rule:
            in_rule = False
    return "\n".join(out)


def patch_client(src):
    idx = src.index(MARK)
    head, tail = src[:idx], src[idx:]
    # CSS 只到模板字符串结束；tail 里只有 CSS（该区块位于 CSS 字面量末尾）
    end = tail.index("`")
    css, rest = tail[:end], tail[end:]
    scoped = scope_css(css)
    out = head + scoped + rest

    old = """        // The Sandrone theme owns the global --dsw-* palette. Do not call
        // theme.overrideTokens here: doing so would repaint the whole window
        // deep blue/violet and erase the black-and-gold integration."""
    new = """        // 皮肤开关：ui.skin = aurora（默认，fairy 自带的深蓝/紫）| workshop（主题的黑金）。
        // 两套配色各自作用域，互不覆盖；切换后需刷新页面。
        void (async () => {
          let skin = 'aurora'
          try {
            const res = await fetch('/sandrone/config', { cache: 'no-store' })
            if (res.ok) {
              const cfg = await res.json()
              if (cfg && cfg.ui && cfg.ui.skin) skin = String(cfg.ui.skin)
            }
          } catch (ignored) { /* 取不到就用默认 */ }
          try {
            document.documentElement.classList.toggle('sdf-skin-workshop', skin === 'workshop')
          } catch (ignored) { /* no dom */ }
          if (skin === 'workshop') return
          try {
            const theme = ctx.get('theme')
            if (theme && typeof theme.overrideTokens === 'function') {
              ctx.effect(() => theme.overrideTokens('sandrone-fairy', SANDRONE_TOKENS), 'sandrone-fairy.theme')
            }
          } catch (error) {
            try { console.error('[sandrone-fairy] theme', error) } catch (ignored) { /* no console */ }
          }
        })()"""
    assert out.count(old) == 1, "anchor missing"
    return out.replace(old, new)


def patch_index(src):
    if '"ui"' in src:
        return src
    out = src.replace(
        "    voice: {",
        "    ui: { skin: 'aurora' },   // aurora = fairy 自带深蓝/紫；workshop = 黑金主题\n    voice: {",
        1,
    )
    return out


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)

    client = patch_client(read(CLIENT))
    write(CLIENT, client)
    write(INDEX, patch_index(read(INDEX)))

    # 版本与变更记录
    pkg = read(os.path.join(FAIRY, "package.json"))
    pkg = pkg.replace('"version": "0.7.7"', '"version": "0.7.8"', 1)
    write(os.path.join(FAIRY, "package.json"), pkg)

    top = read(os.path.join(OUT, "CHANGELOG.md"))
    entry = """## 1.0.1 — 2026-10-27

- **fairy 升级到 0.7.8**：把原作者当前的深蓝/紫 UI 并回来，作为可切换皮肤 `ui.skin`。
  - `aurora`（默认）：恢复 fairy 自己的 `--dsw-*` token 覆盖与深蓝紫面板，窗口整体回到冷色调。
  - `workshop`：沿用 1.0.0 的黑金皮肤（原先无条件的 `!important` 覆盖已收敛到 `html.sdf-skin-workshop` 作用域下）。
  - 切换方式：`POST /sandrone/config {"ui":{"skin":"workshop"}}`，刷新页面生效。
- fairy 版本号 0.7.7 → 0.7.8（皮肤开关 + 配色作用域化），其余行为不变。

"""
    top = top.replace("## 1.0.0", entry + "## 1.0.0", 1)
    write(os.path.join(OUT, "CHANGELOG.md"), top)

    # 文档：把皮肤开关写进 fairy 的 README 与 INTEGRATION
    doc = """

## 皮肤开关（1.0.1 新增）

| 配置 | 值 | 效果 |
|---|---|---|
| `ui.skin` | `aurora`（默认） | fairy 自带的深蓝/紫：整窗 `--dsw-*` token 覆盖 + 深蓝紫面板 |
| `ui.skin` | `workshop` | 沿用「桑多涅 · 人偶工坊」的黑金皮肤：不覆盖 token，面板改用黑金作用域样式 |

切换方式：

```powershell
curl.exe -X POST http://127.0.0.1:<端口>/sandrone/config -H "content-type: application/json" -d "{\"ui\":{\"skin\":\"workshop\"}}"
```

**切换后刷新页面生效**（token 覆盖只在启动时应用一次）。两套样式互斥、作用域隔离，不会互相染色。
"""
    for name in ("README.md", "INTEGRATION.md"):
        path = os.path.join(FAIRY, name)
        if os.path.isfile(path):
            body = read(path)
            if "皮肤开关（1.0.1 新增）" not in body:
                write(path, body.rstrip() + "\n" + doc)

    zip_path = os.path.join(WS, "dsh-theme-sandrone-1.0.1.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    files = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, _dirs, names in os.walk(OUT):
            for name in names:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, OUT)
                z.write(full, os.path.join("dsh-theme-sandrone-1.0.1", rel))
                files += 1
    print("merged files:", files, "zip:", round(os.path.getsize(zip_path) / 1048576, 2), "MB")


if __name__ == "__main__":
    main()
