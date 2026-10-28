# Credits

## Opening score

- **Impact Moderato** — Kevin MacLeod ([incompetech.com](https://incompetech.com/music/royalty-free/))
  Licensed under [Creative Commons: By Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
  Changes made for this project: a 16.6-second excerpt (from 0:02.4), fades, and layering with original synthesized sound design (sub impacts, whooshes, mechanical ticks, glitches, riser, shimmer), mixed and encoded to AAC. The synthesized layers are original to this repository; the underlying composition and recording remain Kevin MacLeod's.
- **Opening voice clips** — extracted from the Bilibili compilation [BV1nJTB6bEhs](https://www.bilibili.com/video/BV1nJTB6bEhs). They are mixed into `opening-score-local.m4a` (the full opening score). Rights in the performances remain with their original rights holders.

## Workshop gramophone (main-interface BGM)

- **致新生（去人声）** — HOYO-MiX / 《原神》6.7 桑多涅角色预告，去人声版来自 B 站 [BV1SgKf6wE9U](https://www.bilibili.com/video/BV1SgKf6wE9U/). 仅作个人本地主题使用；音乐权利归 HOYO-MiX / 原权利人。
- **淑女最后的答案（La dernière question, et sa réponse）** — HOYO-MiX / 《原神》，来自用户提供的本地文件。仅作个人本地主题使用。
- **桑多涅的重生（过场动画）** — HOYO-MiX / 《原神》6.7 过场动画 BGM，去人声版来自 B 站 [BV1W9TB6KEUi](https://www.bilibili.com/video/BV1W9TB6KEUi/). 仅作个人本地主题使用。

三首曲目都做了 `loudnorm=I=-18:TP=-2:LRA=11` 的统一音量处理，并转码为 48 kHz AAC 192 kbps。它们**不是** CC BY 素材，不随 MIT 代码许可再授权；公开上传、镜像或再分发前请先取得相关权利人的许可。

## Fairy assets and fixed voice

- **Desktop-pet artwork, `cine.jpg`, and 48 fixed voice clips** — from the collaborator's `sandrone-fairy 0.7.7` bundle. Character art belongs to HoYoverse / the original rights holders. The fixed clips were synthesized with a GPT-SoVITS voice fine-tuned on official character voice; performance rights remain with the voice actor and original rights holders. They are **not MIT**, are included only for personal local use, and are not licensed for public redistribution.
- The GPT-SoVITS engine and weights are **not** included; only the fixed clips ship. See `dsh-plugin-sandrone-fairy/NOTICE.md` and the root [ASSET-LICENSE.md](ASSET-LICENSE.md).

## Collaborator · 合作者

- **[是雪夕捏](https://space.bilibili.com/662792249)**（B站 UP 主）——`sandrone-fairy` 的合作者：提供语音引擎（GSV-TTS-Lite 双引擎）、四情绪池导演层、控制台、安装自检、档位降级与 48 条预制台词。

## Artwork

- Character art, portrait, background and the 4K opening still are derived from the user-supplied `sandrone-codex` asset set and the provided Wallpaper Engine item. They are **not** MIT and are not licensed for public redistribution; see [ASSET-LICENSE.md](ASSET-LICENSE.md) and [PROVENANCE.json](PROVENANCE.json).
- Sidebar ornament art derives from the same upstream asset set.

## Code and text

- DSH port, installation scripts, preview harness and the persona prompt text: MIT, see [LICENSE](LICENSE).
- Upstream [fengye337/sandrone-codex](https://github.com/fengye337/sandrone-codex): MIT code; assets under their own terms.
- DeepSeek Harness is a third-party application. This is an unofficial fan theme, not affiliated with or endorsed by OpenAI, HoYoverse / COGNOSPHERE, or DeepSeek.
