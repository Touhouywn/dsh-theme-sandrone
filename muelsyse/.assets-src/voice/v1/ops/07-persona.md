# 07 人格：对话与推理用缪尔赛思语气

## 目标
DSH 对话与推理输出使用缪尔赛思语气。插件 Pro 已写好（`E:\AI-theme\muelsyse\dsh-plugin-muelsyse-persona`），flash 只装不改。

## 步骤
1. 安装：
   ```powershell
   pwsh -File E:\AI-theme\muelsyse\dsh-plugin-muelsyse-persona\install.ps1
   ```
2. 关掉哥伦比娅人格（两个同伴人格不能同时生效）：
   - 先备份：复制 `C:\Users\yuanshuifehe\.dsh\profiles\desktop\cordis.patch.yml` 为 `cordis.patch.yml.bak-muelsyse-<ts>`。
   - 编辑原文件：在 `columbina-persona` 条目（`id: columbina-persona` 那个 insert 块）里加一行 `      disabled: true`。
   - 不删条目；`sandrone-persona` 与 `muelsyse-persona` 条目不动。
3. 验证控制路由：
   ```powershell
   curl.exe -s http://127.0.0.1:61212/muelsyse-persona/status
   ```
   期望 200 + `"enabled":true`。404 → HOLD。
4. 冒烟：刷新 Web GUI 后发一句「博士，你在吗」，确认回复是缪尔赛思语气；再问一个技术问题（如「列一下 voicekit 的子命令」），确认命令与事实精确、推理过程也带语气。任一不满足 → 贴样例。

## 断言
- patch 里存在 `muelsyse-persona` 条目且无 `disabled`；`columbina-persona` 条目有 `disabled: true`。
- status 路由 200。
- 冒烟通过。

## 降级表
- 路由 404 → HOLD，贴状态。
- 语气未生效 → 检查 patch 尾 20 行（缩进、BOM），贴出来。
- 想切回哥伦比娅 → 反向操作（columbina 去 disabled、muelsyse 加 disabled），这是 P2 用户决定，flash 不自动做。

## 回报
按 ops\README.md §7。
