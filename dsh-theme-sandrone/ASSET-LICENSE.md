# 素材权利说明

本发行包中，**DSH 移植代码**（`lib/`、`theme/theme.css`、安装脚本、README 等）采用 MIT，见 `LICENSE`。

**桑多涅名称、角色图、视频、签名参考及衍生素材不属于 MIT 授权范围。**

## 上游

本主题是 [fengye337/sandrone-codex](https://github.com/fengye337/sandrone-codex) 的 DSH 移植版，参考其 `themes/sandrone`、`assets/`、开屏与素材组织方式。

- 上游代码：MIT（`LICENSE`）。
- 上游素材：明确保留原权利人权利，不提供额外再授权。
- 上游 `ASSET-LICENSE.md`：<https://github.com/fengye337/sandrone-codex/blob/main/ASSET-LICENSE.md>
- 上游 `asset-edition.json` 写明：`User-supplied third-party artwork; no public redistribution permission is granted by this code license.`
- 上游 `assets/PROVENANCE.json` 列出每个素材与 SHA-256。

## 本包内的素材

`assets/` 中：

- `burst.png`、`cryo.png`、`gear.png`、`icon.png`、`iris.png`、`skill.png`、`strings.png`、`trace.mp4` 与上游 `assets/PROVENANCE.json` 中的对应文件**逐字节一致**；
- `background.webp` 由上游 `assets/backgrounds/dark-mechanical.jpg` 转码而来；
- `portrait.webp` 由上游 `assets/characters/sandrone/portrait.png` 转码而来；
- `opening-art.webp` 由用户提供的 Wallpaper Engine 视频取帧、缩放为 2560×1440 WebP；
- `opening.json` 是由上游轮廓/签名数据整理出的派生数据；
- `opening-score.m4a` 是 Kevin MacLeod *Impact Moderato*（CC BY 4.0）的剪辑 + 原创合成音效；`opening-score-local.m4a` 额外混入从 B 站语音合集提取的片段，随仓库提供。

逐文件来源、SHA-256 与转换说明见 `PROVENANCE.json`；配乐与语音署名见仓库根目录的 `CREDITS.md`。

## 再分发

- 本发行包**不提供**这些素材的额外再授权；公开上传、镜像、打包下载或商业使用前，请先取得相关权利人的许可。
- 仅个人本地安装、自己使用，风险与授权仍由使用者自行确认。
- 如果相关权利人对素材有异议，请通过发行渠道指出对应文件与权利依据，以便移除或替换。

非官方同人主题，与 OpenAI、HoYoverse / COGNOSPHERE、DeepSeek 均无隶属或背书关系。
