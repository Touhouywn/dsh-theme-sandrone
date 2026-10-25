# Sandrone Workshop — DSH 左侧栏入口

给 **Sandrone · 人偶工坊** 主题配的左侧栏入口。点开「桑多涅工坊」会进入一个主题控制台：

- 实时读取 `/theme-sandrone/status`：主题路由、样式表命中、页面自检、深色属性、开屏状态；
- 展示主题的五色配色；
- 一键刷新状态、复制诊断 JSON、重播开屏；
- 切换桑多涅语气（调用 `/sandrone-persona/toggle`，只影响下一条回复；未安装语气插件时显示「未安装」）；
- 运行时不写 profile、不改 DSH 配置、不碰其他插件；安装脚本只追加自己的 patch row。主题仍由 `dsh-theme-sandrone` 提供。

## 结构

```
dsh-plugin-sandrone/
  package.json          # bundle patch + dsh.client 声明
  index.js              # 宿主半边：/sandrone-hub/status 自检路由
  client.js             # 浏览器半边：侧栏行 + 主面板
  cordis.patch.yml      # 作为 bundle 安装时插入的 row
  locale/{zh,en}.json   # 插件管理器里的标题/说明
  icon.svg              # 原创齿轮图标
  install.ps1           # 复制到 ~/.dsh/plugins、链接 profile 并追加 patch row
```

## 安装

```powershell
pwsh -File .\install.ps1
```

脚本会：

1. 把入口包复制到 `%USERPROFILE%\.dsh\plugins\sandrone-hub`，解压目录删掉也不影响；
2. 在 `%USERPROFILE%\.dsh\profiles\desktop\node_modules\dsh-plugin-sandrone` 建立指向该副本的 junction；
3. 在 `cordis.patch.yml` 追加 `sandrone-hub` 的 insert row（已存在则跳过），并先备份 patch；
4. 清理 `package.json` / patch 的 UTF-8 BOM（DSH 启动时对 BOM 是 fatal）。

配置层由 HMR 监听，通常不需要重启；如果侧栏没有出现「桑多涅工坊」，完整退出 DSH 再打开一次。

## 验证

侧栏出现「桑多涅工坊」后，点开应看到主题状态卡片。也可以从外部查：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:<GUI端口>/sandrone-hub/status
```

返回 `pings >= 1` 说明客户端半边已经挂载。

## 卸载

删除 `node_modules\dsh-plugin-sandrone` 的 junction 和 `plugins\sandrone-hub`，并从 `cordis.patch.yml` 移除 `sandrone-hub` 的 insert 块即可；插件不改 profile 的其他内容。发行包根目录的 `uninstall.ps1` 会一起处理。
