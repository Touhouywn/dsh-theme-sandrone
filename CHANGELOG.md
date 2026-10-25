# Changelog

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
