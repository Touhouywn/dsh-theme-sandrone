# Changelog

## 0.4.0 — 2026-10-25

- **电影式开屏 v2**：4K 立绘、启动 HUD（进度 / 时钟 / 诊断行）、金线描边、手写签名、命中闪光与 16 秒时间轴；点击 / 任意键跳过，22 秒硬兜底。
- **开屏配乐**：Kevin MacLeod *Impact Moderato*（CC BY 4.0）剪辑 + 原创合成音效；完整版混入语音片段，`opening-score.m4a` 保留无人声回退。
- **语气插件** `dsh-plugin-sandrone-persona`：`ctx.systemPrompt.section()` 注册可开关的人格段，`/sandrone-persona/status` 与 `/toggle` 控制，下一条回复生效。
- 宿主半边新增 `opening-art.webp` / `opening-score.m4a` / `opening-score-local.m4a` 路由，并支持 HTTP Range（音视频流式读取与 206）。
- 新增 `preview/serve-opening.py` 离线开屏预览、`tools/build-opening-media.py` 配乐构建脚本。
- 新增 `SECURITY.md`、`docs/release-checklist.md`、`tools/build-release.py`；发行包可复现并带 SHA-256。
- 侧栏工坊（0.2.0）新增「对话语气」状态行与「切换语气」按钮，直接调用 `/sandrone-persona/toggle`，只影响下一条回复。
- 根目录安装 / 卸载脚本改为处理三个包；新增 `CREDITS.md` 与 `docs/bgm-options.md`。
- 移除不再使用的 `assets/opening.mp4`（约 9 MB）。

## 0.3.0 — 2026-10-25

- 新增配套侧栏入口包 `dsh-plugin-sandrone`（「桑多涅工坊」）：主题状态、五色配色、诊断 JSON、重播开屏。
- 两个包都改为标准 DSH bundle（`dsh.bundle.patch` → `cordis.patch.yml`），支持插件管理器安装。
- 新增 `locale/{zh,en}.json`，插件管理器里显示本地化标题与说明。
- 补齐 `LICENSE`、`ASSET-LICENSE.md`、`PROVENANCE.json`、`THIRD-PARTY-NOTICES.md`。
- 根目录 `install.ps1` / `uninstall.ps1` 一次处理两个包；安装脚本增加 BOM 清理与 patch 备份。
- 主题包 README 改为发行包口径；新增 `/sandrone-hub/status` 自检路由。

## 0.2.0 — 2026-10-24

- 主题本体：`--dsw-*` token 覆盖、画布立绘、阅读遮罩、玻璃侧栏。
- 开屏动画：`opening.mp4` + `trace.mp4` 双层时序、SVG 描边、手写签名。
- 宿主半边 `/theme-sandrone/*` 资源路由、index 注入、`/theme-sandrone/status` 自检。
- 纯 CSS 侧栏图标覆盖；离线预览页与 `tools/` 自检脚本。
