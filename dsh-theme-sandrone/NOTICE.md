# NOTICE — 来源与权利

本主题是 [fengye337/sandrone-codex](https://github.com/fengye337/sandrone-codex) 的 **DSH 移植版**，参考其 `themes/sandrone`、`assets/`、开屏与素材组织方式（上游提交 `8574a24c7e3e226a49cb8dd1b4b54e22874fb129`）。

## 代码

- 本仓库新增的 DSH 移植代码（`lib/index.js`、`lib/client.js`、`theme/theme.css`、安装脚本）：MIT。
- 上游 sandrone-codex 项目代码：MIT（见上游 `LICENSE`）。
- 上游使用的 Codex Dream Skin 运行时：MIT（commit `6fc42df48a6a5365011f55cc349e20c038e56d1d`）。

## 素材

`assets/` 中的素材**不属于 MIT**，本包不提供额外再授权：

- `burst.png`、`cryo.png`、`gear.png`、`icon.png`、`iris.png`、`skill.png`、`strings.png`、`trace.mp4` 与上游 `assets/PROVENANCE.json` 中的对应文件逐字节一致；
- `background.webp` 由上游 `assets/backgrounds/dark-mechanical.jpg` 转码；
- `portrait.webp` 由上游 `assets/characters/sandrone/portrait.png` 转码；
- `opening-art.webp` 由用户提供的 Wallpaper Engine 视频取帧、缩放为 2560×1440 WebP；
- `opening.json` 是由上游轮廓/签名数据整理出的派生数据；
- `opening-score.m4a` 是 Kevin MacLeod *Impact Moderato*（CC BY 4.0）的剪辑 + 原创合成音效；`opening-score-local.m4a` 额外混入从 B 站语音合集提取的片段，不随公开仓库发布。

上游 `ASSET-LICENSE.md` 说明角色名称、形象及游戏美术保留原权利人权利；上游 `asset-edition.json` 明确写明 **不授予公开再分发许可**（`no public redistribution permission is granted by this code license`）。逐文件来源与 SHA-256 见发行包根目录的 `PROVENANCE.json`。

## 声明

非官方同人主题，与 OpenAI、HoYoverse / COGNOSPHERE、DeepSeek 均无隶属或背书关系。个人本地使用前也请自行确认素材授权；公开上传、镜像、打包下载或商用前必须先取得相关权利人的许可。
