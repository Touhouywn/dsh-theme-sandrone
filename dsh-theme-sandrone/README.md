# Sandrone · 人偶工坊 — DSH 主题

一个可以直接安装到 **DeepSeek Harness Web GUI** 的深色主题：

> **素材授权提示**：主题代码是 MIT；`assets/` 里的桑多涅角色图、视频、签名等第三方素材 **不是 MIT**。上游 `sandrone-codex` 不授予公开再分发许可；公开传播前请先取得权利人许可。详见 [NOTICE.md](NOTICE.md) 与发行包根目录的 `ASSET-LICENSE.md`。

- 黑金配色：深蓝黑画布、象牙白正文、金铜品牌色、冰蓝链接、绯红强调。
- 桑多涅立绘铺在窗口右侧，正文列叠一层可读性遮罩。
- 玻璃侧栏、金色焦点环、暖色代码块、金色滚动条。
- 开屏动画：齿轮/水纹描边 + 彩色正片交叉淡化 + 手写签名。

本目录只包含主题本体。发行包里的 `dsh-plugin-sandrone/` 是配套的左侧栏「桑多涅工坊」入口，可选安装。

## 安装

### 从发行包（推荐）

如果你拿到的是 `dsh-theme-sandrone-0.3.0.zip`，在解压目录运行：

```powershell
pwsh -File .\install.ps1
```

会同时安装主题和侧栏入口。只想要主题：

```powershell
pwsh -File .\dsh-theme-sandrone\install.ps1
```

### 单独使用本目录

```powershell
pwsh -File .\install.ps1
```

脚本会：

- 复制主题到 `%USERPROFILE%\.dsh\themes\sandrone`；
- 在 desktop profile 的 `node_modules` 建立 `dsh-theme-sandrone` junction；
- 在 `cordis.patch.yml` 追加 `theme-sandrone` 行（先备份，已存在则跳过）；
- 清理 `package.json` / patch 的 UTF-8 BOM。

安装后完整退出 DSH 再打开一次。

### 用 DSH 插件管理器

本包是标准 bundle：`package.json` 的 `dsh.bundle.patch` 指向 `cordis.patch.yml`。在插件管理器里选择“安装本地 bundle / 安装文件夹”，指向本目录即可。

### 手动安装（macOS / Linux）

1. 复制本目录到 `~/.dsh/themes/sandrone/`。
2. 建立链接 `~/.dsh/profiles/desktop/node_modules/dsh-theme-sandrone` → 该目录。
3. 在 `~/.dsh/profiles/desktop/cordis.patch.yml` 末尾追加：

   ```yaml
   - insert:
       - id: theme-sandrone
         name: dsh-theme-sandrone
   ```

4. 完整退出并重新打开 DSH。

## 验证

```text
http://127.0.0.1:<GUI端口>/theme-sandrone/status
```

返回 `theme: "sandrone-marionette"` 即主题宿主半边已挂载；页面应显示立绘与黑金配色。

## 卸载

```powershell
pwsh -File .\uninstall.ps1
```

移除 patch row 和 junction；主题文件默认保留，加 `-Purge` 一并删除。

## 兼容与排障

- 针对 DSH `0.2.1-rc.3` 验证；使用 `--dsw-*` token 和 CSS Module 的稳定类名后缀，小版本升级通常仍然可用。
- 升级后立绘/图标消失：多半是 DSH 改了 `centerCol` / `sidebarCol` / `composer` 等后缀或 token 名，改 `theme/theme.css` 对应选择器即可。
- DSH 起不来：检查 profile 的 `package.json` 是否有 UTF-8 BOM；安装脚本会自动清理。
- 主题自检：`/theme-sandrone/status`。

## 许可与素材

- 主题代码（`lib/`、`theme/theme.css`、脚本）：MIT。
- 桑多涅角色图片、开屏视频、签名等素材：权利归原权利人，**不适用 MIT**；本包不提供额外再授权。
- 上游：[fengye337/sandrone-codex](https://github.com/fengye337/sandrone-codex)（代码 MIT；素材见其 `ASSET-LICENSE.md` 和 `assets/PROVENANCE.json`）。
- 逐文件来源与 SHA-256 见发行包根目录的 `PROVENANCE.json`；权利说明见 `NOTICE.md` / `ASSET-LICENSE.md`。
- 非官方同人主题，与 OpenAI、HoYoverse / COGNOSPHERE、DeepSeek 均无隶属或背书关系。公开分发前请确认素材授权。
