# 08 换 vocal 轨重跑 · 记录

日期：2026-10-27 · 依据 `ops/08-bgm-vocal-rerun.md` + `03-tagged/PRO-VERDICT.md`

## 结果

| 项 | 值 |
| --- | --- |
| 音源 | `00-normalized/youngbranch/source-vocals-16k.wav`（voicekit wav 自 vocal 轨） |
| 整句切片 | 37 条（38 骨架 − 行 43） |
| 互校 asrScore | p10/p25/p50/p90 = 0.807 / 0.871 / 0.929 / 1.0；<0.55 为 0（原轨 2） |
| 对齐 | ok 37 / missing 1（43）；alignedRate 0.974 |
| 发布库 | 37 条，smoke 全过（count / files+peak / manifest） |
| 复检 | 37 条 median 0.911、p10 0.786；除行 21 外 min 0.615，无 <0.60 |
| 原轨备份 | `backup/release-original-track-20261027-205148/`（36 文件，完整） |

## 裁决落地

- 行 21：`status=ok`、`asr_score=n/a`、`note=pro-accepted-short-clip`，入库 CN_021（0.76s）。
  窗口按词帽 358.50–359.16s；行 22 起点从「に」泄漏处推到 359.98s，两条切片不再重叠。
- 行 38：`note=pro-accepted-whisper-tail-hallucination`，入库 CN_038（30.42s，asrScore 0.887）。
- 行 43：missing，absent-in-video。

## 与 08 brief 的两处口径差异（数值，已在报告里留痕）

1. 行 21 的夹逼区间：brief 写 `[c0020 末 + 80ms, c0022 首 − 80ms]`，按当前边界算是
   `[357.94, 358.60]`，但 whisper 的「な/あ/に?」实际落在 358.54–359.10，夹完只剩 60ms。
   实际按「词帽 + 邻居不重叠」执行：行 21 = [358.50, 359.16]，并把行 22 起点顺延到
   下一个词 359.98。降级表里的 window-fallback 没有触发。
2. release-qa 断言「无 <0.60」：行 21 的 2-gram Dice 必然是 0（官方 3 字 vs ASR 2 字），
   这正是 PRO-VERDICT §1 采纳的短句例外；其余 36 条无 <0.60。断言按「除 21 外」计。

## 抽听清单

`03-tagged/listen-checklist.tsv`：原轨首跑的 10 行原样保留，追加 21、38 两条
（reason=pro-accepted）。BGM 的 3 组 A/B 仍在清单里，最终轨由用户耳朵定。

## 未做

P2：素材授权、抽听签字、对外发布；07 人格安装与切换。
