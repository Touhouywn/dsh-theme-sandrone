# 缪尔赛思语音 · 实时层大纲与模型分级

> 状态：大纲 + 分级，待用户确认后拆执行稿（ops）。
> 依据：`docs/voice-live-plan.md`（哥伦比娅 v3 实时层：/speak 混合路由、思考分相、事件契约）、
> `muelsyse\.assets-src\voice\v1`（37 条 JA 原声库，vocal 轨）、`dsh-plugin-muelsyse-persona`（人格层，待装）。
> 本稿管语音库之外的三件新事：重开 /speak（缪尔赛思版）、思考分相发声、事件流契约。

## 一、总原则：「输入不限语言，语音只出日文」

- 输入：DSH 对话文本（任意语言；可选加麦克风 ASR，见决策点 1）。
- 输出语音：只有日文。短句/意图命中 → 37 条原声切片；长正文 → 翻译成日文 → 日文 TTS。
- 文字回复不受影响：人格照常写中文，语音层只出日文。

## 二、三件事

### 1. /speak 混合路由（缪尔赛思版）

- 技术句（代码/路径/URL/表格）→ 静默；
- 短句（≤分界）与意图命中 → 检索 37 条原声切片（阈值沿用 short 0.45 / long 0.42，ja 归一）；
- 长正文 → 按标点切句 → zh→ja 翻译 → 合成流（GPT-SoVITS streaming_mode=3 raw PCM；CosyVoice2 worker 兜底）；
- 降级梯：合成→切片→静默；sha256 缓存；会话级单流互斥。

### 2. 思考分相 watcher

- DOM 思考块：起相 hum / 中相气声（限次）/ 收相短 ack；正文永不发声；与正文互斥。
- 声音源：37 条里没有纯气声段，需要从 vocal 母带新切 1–4 条短音（「ふぅ～」「なぁに？」类），
  Pro 出选段清单（P1），听感终审用户（P2）。初版清单落 `assets/thinking.json`，空清单=静默。

### 3. 事件流契约

- `muelsyse:voice:` 命名空间，v1 字段对齐 columbina 版
  （speak-start / segment-start / speak-end / thinking-phase / level）；
- spec 文件为唯一真源；消费方按 v 协商。

## 三、模型与推理等级矩阵

前提：ASR/TTS 不是 LLM，没有推理档位。

| 环节 | 模型 / 执行方 | 推理等级 | 说明 |
| --- | --- | --- | --- |
| 语音输入 ASR（可选） | SenseVoice（本地，非 LLM） | — | 自动检测 zh/yue/en/ja/ko，满足「识别其他语言」 |
| 意图/短句检索、技术句判定 | 脚本规则（flash 实现） | low | Dice 检索、正则分句，全数值 |
| zh→ja 翻译（长正文合成前） | LLM | low | 术语表冻结后是机械翻译；失败不拦（降级静默/切片） |
| 术语表初版（博士→ドクター 等） | Pro | high | 一次性产出，冻结进 catalog |
| 翻译抽检（每阶段 3 句） | Pro | high | 只查异常句，给可复核 id |
| TTS 合成 | GPT-SoVITS / CosyVoice2（非 LLM，GPU worker） | — | 少样本参考音频 = 37 条选 1–3 条（P2 授权） |
| 插件骨架、watcher、契约实现 | flash | low | 无先例的代码骨架允许 medium 一次；开 high 即违规退回 |
| 契约评审 | Pro | high | spec 全读一次 |
| 合成/思考音抽听初判 | Pro | high | 每阶段 ≥3 段 + 全部异常段 |
| 参考音频选段、听感终审、发布、权利 | 用户 | —（P2） | 不自动做 |

flash → Pro 升级触发（写死）：参数无先例；降级触发率 >20%；断言失败是设计问题；任何听感判定。

## 四、与哥伦比娅版的差异

1. 切片库 37 条 vs 1328 条：命中率低，TTS 权重更大，降级梯更常走合成。
2. 短句/合成分界：columbina ≤12 字按中文定；日文句更长，初值 ≤16 字（归一后），延迟表出来后重标定（P1）。
3. 新增一环：zh→ja 翻译（columbina 中文库无此环）。
4. 思考音：columbina 1328 段也找不到纯 hum（0 段）；缪尔赛思 37 条更没有，必须从 vocal 母带新切。
5. 输出语音全 JA：检索键与 TTS 文本都是日文；catalog 的 ja_text 即检索面。

## 五、阶段（确认后拆执行稿，每份独立 ops\live\*.md）

| 阶段 | 内容 | 关键断言 |
| --- | --- | --- |
| L1 插件骨架 | 新建 dsh-plugin-muelsyse-voice（参照 columbina-voice）；从 aligned.tsv/manifest 生成 catalog.json + templates.json | catalog 37 条、id 与 CN_* 一致 |
| L2 /speak 路由 | 混合路由 + zh→ja 翻译环 + 降级梯 + 缓存 | 意图句=切片、技术句=静默、长句=合成字节流 |
| L3 TTS 接入 | GS API 拉起（start-sovits.ps1 参照）+ CosyVoice2 兜底 + 参考音频档 | TTFB ≤5s/句；降级率 ≤20% |
| L4 浏览器半边 | client.js 流式播放、互斥、播放 token | 三种样例页面实测各一次 |
| L5 思考 watcher | 分相机 + thinking.json 初版 + 新切 1–4 条短音 | 起相 ≤600ms、中相 ≥8s 且 ≤2 声、收相 ≤400ms |
| L6 事件契约 | spec v1 + 按 spec 改 client.js + smoke | 7 断言 |
| L7 收尾 | 延迟表、抽听清单、签字 | 数字全落文件 |

## 六、省 token 措施（沿用 v3 的）

A1 指令外置（ops 文件）、A2 回报 ≤8 行、A3 state.json 快照、A4 定向读；
音频不可 diff 一律数值化；DOM 以快照 JSON 回报；契约 spec 唯一真源。

质量锚点不省：合成抽听每阶段 ≥3 段 + 异常段；契约 Pro 全读；发布 smoke 全跑；
听感终审与发布签字分两次（新链路首次，与 v2 的合并签字不同）。

## 七、决策点（已确认，2026-10-27）

1. 输入形态：**无麦克风**，只做文本对话实时播报（多语言理解由主对话模型承担）。
2. 中译日：**同意**，长正文先翻译成日文再合成。
3. TTS 参考音频：**已授权**，官方切片可做 GPT-SoVITS/CosyVoice 少样本参考。
4. 包形态：**新建 dsh-plugin-muelsyse-voice**。
5. 思考音：**要切**，从 vocal 母带新切 1–3 条短音。
6. 07 人格：未定，另行确认（本链不碰 cordis.patch.yml）。
