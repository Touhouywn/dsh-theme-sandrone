# L2 /speak 混合路由 + 翻译通道

## 目标
`POST /muelsyse-voice/speak {text}` 成为统一入口：技术句静默、短句原声、长正文中译日后合成，降级梯「合成→切片→静默」。

## 步骤
0. **翻译通道探测（先做，结论写 live-prep 附注）**：
   - 已知：本机 `/api/models` 回 `unauthorized`，说明 /api 面存在但要凭证。
   - 探 `/api/chat`、`/api/chat/completions`、`/api/v1/chat/completions`（带不带凭证各试一次）；
   - 查 `C:\Users\yuanshuifehe\.dsh\llm-deepseek\` 有无可用 key 文件（只读探测，不接线）；
   - 有通道 → 记入 `03-tagged\live-translate-channel.md` 并接步骤 3；没有 → HOLD 回 Pro，本阶段暂停。
1. L4 技术句过滤：代码块/路径/URL/表格 → 该句静默（参照 columbina index.js L77 technical()，正则补日文标点）。
2. 分句 `/[。！？!?；;\n]+/`；归一后 ≤16 字 → 检索 `selectFromText`（Dice short 0.45 / long 0.42，maxClips 2，ja 归一用 pipeline\norm_ja.py 同口径）。
3. 长句 → 中译日：翻译通道（步骤 0 选定）+ 术语表（live-prep §1 注入 system）+ temperature 0 + 低推理；
   翻译失败该句 → 静默 + missing 计数，不整轮失败。
4. 长句合成计划：`GET /synth?text=<ja>&stream=1`（L3 提供）；返回计划 JSON
   `{segments:[{kind:"clip"|"silent"|"tts", text, clip?}]}`。
5. 缓存：sha256(归一 ja 文本) → `%TEMP%\muelsyse-voice-cache\<hash>.wav`；缓存不可写 → 内存直播。
6. 并发：会话级单流，新请求 abort 旧流。

## 断言
- 意图句（如「我该出发了」）→ 计划含 clip 段；技术句 → 空计划；长正文 → tts 段或降级 clip/静默。
- smoke 三例跑过（tools\smoke.mjs 扩展）。

## 参数冻结（初值，改动先改本文件）
| 项 | 值 |
| --- | --- |
| 短句/合成分界 | ≤16 字（归一后；延迟表后 Pro 重标定） |
| 翻译模型 | deepseek-chat 档（低推理），temperature 0 |
| 阈值 | short 0.45 / long 0.42 / maxClips 2 |
| 缓存键 | sha256(归一 ja 文本) |

## 降级表
| 情况 | 动作 |
| --- | --- |
| 翻译通道不可用 | HOLD（步骤 0） |
| 翻译句失败率 >20% | HOLD，贴失败样例 |
| 检索低分 | 该句静默 + missing 计数 |
| 任何听感判定 | 交 Pro |
