# 08 换 vocal 轨重跑（含 Pro 裁决落地）

## 目标
发布库改用 vocal 轨；落地 Pro 三条裁决（21 采纳、38 加回、43 missing）；对重跑结果再做独立复检。

## 前置
- 读 `03-tagged\PRO-VERDICT.md`。
- `02-asr\youngbranch.words.json` 本就基于 vocal 轨，无需重跑 words / vad / rules / 碎片 cut。
- 环境同 RUN-REPORT §6（HF_HOME 指 `E:\AI-theme\muelsyse\.cache\hf`、`HF_HUB_OFFLINE=1`）。

## 步骤
1. 备份：把 `07-release\` 整体复制为 `backup\release-original-track-<ts>\`（不删）。
2. wav16：用 voicekit wav 从 `00-normalized\youngbranch\source-vocals.wav` 生成
   `source-vocals-16k.wav`（同 chain_v4 step_wav16 口径；先备份同名旧文件）。
3. 行 21 窗口修正：在 words.json 里取「何」「な」相关词的最早 start − 40ms 与最晚 end + 60ms
   （词帽口径），区间夹在 [c0020 末 + 80ms, c0022 首 − 80ms]；把该边界写回 linecut 后重切 37 条整句。
4. 重跑：`step02c_linecut`（音源 = vocal-16k）→ `step04_asr` → `step04b_crosscheck` →
   `step04_align` → `step05_audit` → `step06_release`。
5. Pro 裁决落地（写进 aligned.tsv 与 manifest）：
   - 21：status=ok，usable=true，asrScore=n/a，note=pro-accepted-short-clip。
   - 38：usable=true，note=pro-accepted-whisper-tail-hallucination。
   - 43：missing，reason=absent-in-video。
6. release-qa：对发布库逐条重跑 whisper medium ja（与上次同口径），写
   `03-tagged\release-qa-vocal.json`；贴 n / median / p10 / min。
7. 抽听清单：保留原 10 行，追加新库 21 与 38 两条。

## 断言
- 发布库条数 = 37（38 骨架 − 43）。
- 21 与 38 在库且 note 正确；43 在 aligned.tsv 中为 missing。
- release-qa 无 < 0.60 条。
- 原发布库完整留在 backup\release-original-track-<ts>\。

## 降级表
- 21 窗口里找不到「何」「な」的词 → 用 [357.86s+80ms, 358.68s−80ms] 整窗，note 记 window-fallback。
- vocal 轨 ASR 分数显著低于原轨（demucs 吞音迹象）→ HOLD，贴两轨对比表，Pro 定轨。
- 任一步 FAIL → 回滚用 backup\release-original-track-<ts>\。

## 回报
按 ops\README.md §7。
