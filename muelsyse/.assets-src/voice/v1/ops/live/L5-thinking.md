# L5 思考分相 watcher + 切 3 条短音

## 目标
思考块出现 → 起相 hum；持续 → 中相（限次）；收起 → 收相 ack。正文永不发声；与正文互斥。

## 步骤
1. 切短音（音源 `00-normalized\youngbranch\source-vocals.wav`，词帽 + fade 25/40 + 留白 80/120，
   16k mono s16，落 `assets\thinking\`）：
   - `hum.wav`：CN_005 头部「ふぅ～」（源 ~97.06s 起；用 `02-asr\youngbranch.words.json` 里该词区间词帽切，~1.2s）；
   - `mid.wav`：CN_034 头部前 ~2.0s「ふぅ、少なくとも…」（同法）；
   - `ack.wav`：直接复制 `assets\clips\CN_021.wav`（0.76s，已入库不重切）。
2. `assets\thinking.json`：`{version:1, phases:{start:["hum"], mid:["mid"], end:["ack"]}}`
   （v1 初版；听感终审前不扩池）。
3. watcher（client.js）：选择器三候选 `[class*="thinking" i]`、`[class*="reasoning" i]`、
   `[class*="thought" i]`；分相机：起相块出现 ≤600ms 出声、中相 ≥8s 且 ≤2 声、收相 ≤400ms；
   正文出声时思考音让路；分相事件照发（L6 契约）。
4. `tools\test_think.mjs`：6 断言（起/中/收、中相限次、正文让路、恢复）。

## 断言
- 3 个文件存在且时长（hum ~1.2s、mid ~2.0s、ack 0.76s ±0.2s）；test_think 6 断言过。

## 参数冻结
同 columbina：起相 ≤600ms；中相 ≥8s 且 ≤2 声；收相 ≤400ms；空清单=静默。

## 降级表
| 情况 | 动作 |
| --- | --- |
| 清单为空/缺失 | watcher 静默，事件照发 |
| 选择器无命中 | 视为无思考块，惰性 |
| 正文出声 | 思考音跳过，事件照发 |

## P2
三条短音的听感终审归用户；未签字前 v1 清单不进发布。
