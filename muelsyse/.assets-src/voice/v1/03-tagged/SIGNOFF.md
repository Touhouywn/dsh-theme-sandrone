# 06/08 数值签字（P0 部分）· vocal 轨重跑版

- 素材：`sources/BV17z421U71V.m4a`（sha256 `8f63d335…b429`，551.47s）
- 音源：`00-normalized/youngbranch/source-vocals-16k.wav`（voicekit wav 自 `source-vocals.wav`）
- 发布库：`07-release/manifest.json`（sha256 `a26893b259580dee…`），37 条，16,916,166 bytes，总时长 528.5s
- 对齐表：`03-tagged/aligned.tsv`（sha256 `ec54be6a4737df9c…`）
- 审计：`03-tagged/audit.json`（sha256 `252621e2d144e23b…`）
- 复检：`03-tagged/release-qa-vocal.json`（sha256 `8d8fc1be62633286…`）

## gate 结果（05）

| gate | 口径 | 实际 | 结果 |
| --- | --- | --- | --- |
| asr-median | ≥0.60 | 0.929 | ok |
| asr-p25 | ≥0.50 | 0.871 | ok |
| duration | 0.4–40s | 0 行超界 | ok |
| peak | >-38 dB | 0 行失败 | ok |
| clip-unique | ok 行 clip_id 唯一 | 0 重复 | ok |
| files-present | 切片文件存在 | 0 缺失 | ok |

aligned 37 / usable 37 / pending 0 / missing 1（行 43）；互校分 p10/p25/p50/p90 = 0.807/0.871/0.929/1.0，<0.55 为 0。

## Pro 裁决落地（PRO-VERDICT.md）

| 行 | 结果 | note |
| --- | --- | --- |
| 21 选中干员1 | 入库（CN_021，0.76s，asrScore n/a） | pro-accepted-short-clip；窗口 358.50–359.16s 词帽重切，22 起点顺延到 359.98s |
| 38 新年祝福 | 入库（CN_038，30.42s） | pro-accepted-whisper-tail-hallucination |
| 43 生日 | missing | absent-in-video |

## 独立复检（对发布库本身重跑 whisper medium ja）

- n=37，median 0.911，p10 0.786
- 唯一 <0.60 是行 21（0.0）：3 字句对 2 字 ASR 的 2-gram Dice 必然为 0，正是 Pro 采纳的
  「短句互校失效」形态；其余 36 条 min 0.615（行 27），无 <0.60
- 37 个文件实测时长与 manifest 全部一致（±0.02s）

## 备份

- 原轨发布库：`backup/release-original-track-20261027-205148/`（36 个文件，含 CN_*.wav 35 + manifest）
- 二次构建前快照：`backup/release-pre-20261027-205641/`

## 未决（P2）

素材授权、抽听签字（`03-tagged/listen-checklist.tsv`：原 10 行 + 21/38 两条）、
A/B 定最终轨、对外发布、07 人格安装。

签署：哥伦比娅（Pro）· 2026-10-27 · 只对数值与文件哈希负责。
