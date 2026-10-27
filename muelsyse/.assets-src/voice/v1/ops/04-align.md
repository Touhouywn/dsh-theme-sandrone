# 04 对齐 38 行骨架

## 目标
把切片按顺序对齐到 `ROOT\skeleton-38.tsv`（38 行「新枝」官方文本，Pro 已填）。

## 输入 / 输出
- 输入：`skeleton-38.tsv`、`02-asr\youngbranch.json`、`02-asr\youngbranch.cross.json`、`01-slices\youngbranch\clips\index.json`
- 输出：`03-tagged\aligned.tsv`
  列 = 骨架 6 列 + `clip_id,source_start_ms,source_end_ms,dur_s,sense_ja,whisper_ja,asr_score,align_dice,status,note`

## 归一（写一个 norm_ja；04 与 05 共用一份实现，放在 `pipeline\norm_ja.py`）
1. NFKC；只保留 `[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]`。
2. 片假名 → 平假名（U+30A1..U+30F6 减 0x60；长音「ー」丢弃）。
3. 官方 ja_text 与两路 ASR 文本都过同一 norm。

## 对齐算法（写 `pipeline\step04_align.py`，顺序 DP）
- 候选相似度 = 2-gram Dice（同 v2 公式）；对 (行 ja_text, 切片 sense_ja) 与 (行 ja_text, 切片 whisper_ja) 各算一次，取高者记 align_dice。
- 顺序 DP：行 1..38 × 切片按时间序；允许跳过切片（视频插播）与跳行（missing）；贪心即可，低分冲突时输出 top-2 候选（maxClips 2）。
- 门槛：norm 后 ≤12 字 → 0.45；>12 字 → 0.42。
  - dice ≥ 门槛 → status=ok。
  - dice < 门槛 → status=pending-pro（附 top-2 候选与两路文本，交 Pro）。
  - 无候选 → status=missing，note=absent-in-video 或 no-candidate。

## 断言
- 骨架行数 = 38，缺 → STOP。
- aligned 率（ok/38）≥ 0.85，否则 STOP 贴清单。
- ok 行 clip_id 唯一；重复 → STOP。

## 回报
reports：`03-tagged\aligned.tsv`；anomalies 贴全部 pending-pro 与 missing 行（行数不多，贴全）。
