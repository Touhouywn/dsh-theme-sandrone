# L1 插件骨架 + 静态资产

## 目标
新建 `dsh-plugin-muelsyse-voice`，生成 catalog/templates，复制 37 条切片。不写路由逻辑。

## 输入 / 输出
- 输入：`03-tagged\aligned.tsv`、`07-release\clips\CN_*.wav`、`07-release\manifest.json`、
  参照 `columbina\dsh-plugin-columbina-voice\`（package.json / cordis.patch.yml / install.ps1 模式）、
  `live-prep.md` §4/§6。
- 输出：`E:\AI-theme\muelsyse\dsh-plugin-muelsyse-voice\`（package.json、cordis.patch.yml、
  index.js 骨架、install.ps1、uninstall.ps1、locale\、assets\catalog.json、
  assets\templates.json、assets\clips\CN_*.wav、tools\smoke.mjs）。

## 步骤
1. 建目录与 package.json：name `dsh-plugin-muelsyse-voice`、type module、main index.js、
   `dsh.bundle.patch` 指向 cordis.patch.yml；cordis.patch.yml 为
   `- insert: - id: muelsyse-voice - name: dsh-plugin-muelsyse-voice`（照 persona 插件的模式）。
2. 复制 37 个 `CN_*.wav` 到 `assets\clips\`（原样，不转码）。
3. 写 `tools\build_catalog.py`：读 aligned.tsv + manifest.json，生成 assets\catalog.json：
   schema 对齐 columbina v2 ——
   `{version:2, source:"bilibili:BV17z421U71V", clips:[{id:"CN_001", file:"clips/CN_001.wav",
   text:<ja_text>, asrText:<whisper_ja>, duration:<dur_s>, sourceStart:<秒>, sourceEnd:<秒>,
   tags:[<trigger>], stem:"vocals"}]}`。只收 status=ok 的 37 行；21/38 的 note 原样带进 `note` 字段。
4. 生成 assets\templates.json：`{version:1, templates:[{trigger, ids:[...]}]}`，按 trigger 分组。
5. index.js 骨架：只挂 `GET /muelsyse-voice/status`（返回 catalog 条数与 ttsConfigured=false）、
   `GET /muelsyse-voice/catalog`、`GET /muelsyse-voice/clip/<id>`；其余路由 L2/L3 再加，本阶段 404。
6. 写 `tools\smoke.mjs`（node 直跑，断言不依赖 DSH）：catalog 37 条；id 集合与 manifest 一致；
   37 个文件存在且 sha256 与 manifest 一致；templates 无空组。

## 断言
- catalog 37 条、id 与 manifest 一致、clip 文件 sha256 一致、templates 无空组。

## 降级表
| 情况 | 动作 |
| --- | --- |
| 任一断言失败 | STOP，贴差异清单 |
| manifest 与 aligned.tsv 行数对不上 | STOP，贴两边行数 |

## 回报
按 live\README.md §4/§5。
