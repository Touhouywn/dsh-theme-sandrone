# 05 审计

## 目标
数值 gate 全自动 + 抽听清单交 Pro。

## 输入 / 输出
- 输入：`03-tagged\aligned.tsv`、`02-asr\youngbranch.cross.json`、`01-slices\youngbranch\clips\index.json`、`01-slices\youngbranch\clips\*.wav`
- 输出：`03-tagged\audit.json`、`03-tagged\listen-checklist.tsv`

## 步骤（全数值，不自动改阈值）
1. asrScore 分位：p10/p50/p90、<0.55 计数。
   - median < 0.6 或 P25 < 0.5 → HOLD，贴分位，Pro 重标定。
2. 每 ok 行断言：时长 0.4–10s；max_volume > -38 dB；clip_id 唯一。
3. filler 行（0.4–0.6s）逐行核对是短台词（如「なぁに？」），不是切坏。
4. 抽听清单：每源 3 段（首/中/尾）+ 全部 pending-pro 行 + BGM verdict=fail 时的 3 段 A/B →
   写 `03-tagged\listen-checklist.tsv`（行号、clip、状态、抽听原因）。本阶段不做结论，交 Pro（P1）。
5. tailOverrun 复查：index.json 中 sourceEnd−energyEnd > 60ms 的行数 > 1 → STOP。
6. 写 audit.json：{aligned, usable, missing, pending, stats, gates:[{name, ok, actual}]}。

## 回报
verdict + gates 摘要 + pending/missing 清单；reports：audit.json 与 listen-checklist.tsv。
