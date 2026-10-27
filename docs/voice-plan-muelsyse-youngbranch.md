# 语音素材整理大纲 · 缪尔赛思：新枝（YOUNG BRANCH）日文语音集

> 设计：2026-10-27。依据：voicekit 工具链 + `docs/voice-pipeline-sop-v2.md`（已审核 v1.0）。
> 素材：《明日方舟》缪尔赛思 时装「新枝」日文语音集，CV 田村由加莉，B 站 BV17z421U71V。
> 分工（已定）：Pro（本会话）出执行稿与语义裁决（P1）；flash 按 ops 执行稿跑（P0 数值自动）；素材授权、抽听签字、发布归用户（P2）。

## 一、目标

把整段语音集视频整理成一套句级语音素材库：

- 语音行按 PRTS「新枝」官方模板对齐（38 行）
- 每行一个句级切片（vocal 轨、去 BGM，BGM 判定数值自动）
- 日文转写（SenseVoice 主 + faster-whisper 互校）+ 中文列 = PRTS 官中文本（已定，见 `muelsyse\.assets-src\voice\v1\skeleton-38.tsv`）
- 输出 aligned.tsv + 审计报告 + 07-release 发布库

## 二、素材事实

- 标题：【明日方舟·日文语音集·皮肤语音】缪尔赛思：新枝 Muelsyse: YOUNG BRANCH【CV. 田村由加莉】
- 类型：皮肤语音集（时装语音），日语；来源：B 站 BV17z421U71V
- PRTS 语音 key：char_249_mlyss；「新枝」日文路径 voice/char_249_mlyss_boc__8
- 官中/日文官方文本已从 PRTS 语音记录页取得（38 行，含触发类型），成为对齐骨架

待确认（00 阶段核实）：时长、音轨编码、是否混 BGM。

## 三、目录（v1，与 columbina v2 同构）

```
E:\AI-theme\muelsyse\.assets-src\voice\v1\
  skeleton-38.tsv      官中/日文 38 行骨架（Pro 已填，只读）
  sources\             BV17z421U71V.m4a
  00-normalized\       source.wav(48k) / source-16k.wav / source-vocals.wav / meta.json
  01-slices\           vad.json / segments.json / clips\（+index.json）
  02-asr\              youngbranch.json / youngbranch.cross.json / youngbranch.words.json
  03-tagged\           aligned.tsv / audit.json / listen-checklist.tsv
  01-separate\         demucs 中间件 / floor-drop.json
  07-release\          clips\CN_<prts_idx>.wav + manifest.json
  backup\              发布前备份
  pipeline\            v2 脚本副本（仅路径与语言两处改造，见 ops\README.md §3）
  ops\                 flash 执行稿（本大纲的落地件）
  logs\  state.json
```

## 四、执行稿（ops）索引

flash 按序执行，每阶段回报 verdict/changed/diff/anomalies/reports，全量报告落文件：

| 稿 | 内容 | 关键决策 |
| --- | --- | --- |
| ops\README.md | 总纲：路径、预备改造、冻结参数、降级总表 | 改动必须先改此文件 |
| ops\00-acquire.md | yt-dlp 下载 + 探测 | 清华源 → 代理 → HOLD 用户手动放文件 |
| ops\01-normalize.md | 48k/16k、loudnorm | 时长 ±0.1s、peak ≤-1.5 断言 |
| ops\01.5-separate.md | htdemucs vocal + 数值 BGM 判定 | preLowShare ≥0.15 且 dropDb ≥3 |
| ops\02-slice.md | 词时间戳 → vad → 规则 → 切 | ja：whisper medium；词帽 40/60 |
| ops\03-asr.md | SenseVoice + whisper 互校 | 正则含假名；asrScore 6:4 Dice/包含 |
| ops\04-align.md | 顺序 DP 对齐 38 行骨架 | 短 0.45 / 长 0.42；pending-pro 交 Pro |
| ops\05-audit.md | 数值 gate + 抽听清单 | 阈值不足 → HOLD，Pro 重标定 |
| ops\06-release.md | usable 过滤 + smoke + 备份 | 发布动作等用户签字 |
| ops\07-persona.md | 安装缪尔赛思人格插件、切换语气 | 关哥伦比娅人格（可逆）；对话与推理同生效 |

## 五、模型与推理等级矩阵

前提：推理等级只对 LLM 有意义。转码 / 分离 / 切分 / ASR 是数值或语音模型，没有推理档位。

| 环节 | 模型 | 推理等级 | 说明 |
| --- | --- | --- | --- |
| 00–02 获取/转码/分离/切分 | 无 LLM（yt-dlp·ffmpeg·htdemucs·v2 pipeline） | — | 参数冻结，脚本执行 |
| 03 主转写 | voicekit SenseVoiceSmall（本地 CPU） | —（ASR） | 自动检测，支持 ja；不是权威 |
| 03 互校 | faster-whisper medium（ja，int8 CPU） | —（ASR） | 双模型互校是 usable 判定的前提 |
| 04 对齐初排 | flash（低推理，脚本） | 低 | 顺序 DP + Dice，机械 |
| 04/05 语义裁决 | Pro（本会话，高推理） | 高 | pending-pro 行、missing 定性、听感 |
| 06 发布 | 脚本 + 用户 | —（P2） | 抽听签字与发布合并一次 |

分工原则：P0 数值 → 脚本自动；P1 语义 → Pro；P2 授权/签字/发布 → 用户。

## 六、主题层（后续再议，不抄桑多涅）

- 人格层已先行：`E:\AI-theme\muelsyse\dsh-plugin-muelsyse-persona` 由 Pro 写好，flash 按 ops\07-persona.md 安装后，对话与推理即用缪尔赛思语气（systemPrompt 段对思考同样生效）；与哥伦比娅人格互斥、可逆。
- 主题包 dsh-theme-muelsyse 的实现方案等语音库完成后再议，届时 Pro 出 2–3 套方案供选择。
- 已记录的需求：实时语音需识别其他语言（SenseVoice 已支持 zh/yue/en/ja/ko，与现链一致）、播放日文切片；骨架的 trigger 列（HOME_SHOW / BATTLE_SELECT 等）即为未来意图键。
