# P1 裁决书 · 缪尔赛思「新枝」v1

日期：2026-10-27 · 裁决人：哥伦比娅（Pro）

## 1. 行 21「选中干员1」— 采纳（usable）

- 官方文本 3 字「なぁに？」；两路 ASR 出的「な」「何?」都是官方文本的子串碎片，不是乱码。
- 位置锚：夹在 c0020（末 357.86s）与 c0022（首 358.68s）之间，视频按行序播放，没有别的行可放。
- 旁证：c0022 的 whisper 转写以「に」开头——那是行 21 句尾泄漏进 22 的头部，证明语音在轨上。
- 处置：采纳。窗口按词帽修正后重切（见 ops\08）；asrScore 记 n/a，note=pro-accepted-short-clip。
- 仍入抽听清单；最终以用户耳朵签字为准。

## 2. 行 38「新年祝福」— 加回（usable）

- align_dice 0.962、SenseVoice 全文正常；asrScore 0.29 系 whisper 30.4s 尾窗幻觉
  （「ご視聴ありがとうございました」），不是内容错误。
- 双引擎互校在 >30s 长句上系统性失灵，不以此拦行。
- 处置：usable=true，note=pro-accepted-whisper-tail-hallucination；入抽听清单。

## 3. 行 43「生日」— 维持 missing

- 42→44 间隙仅 1.3s，容不下 99 字整句；absent-in-video 成立。
- 处置：missing，reason=absent-in-video。最终库 = 37 行（38 骨架 − 43）。

## 4. BGM — 建议换 vocal 轨并重跑

- dropDb 10.89 ≥ 3（pass 线），lowShare 0.0199 < 0.15 只说明 BGM 非低频为主（钢琴/氛围类），
  是 lowShare 判据失灵的典型形态，不是「没有 BGM」。
- 整轨 −20 dBFS 底噪 + 10.89 dB 能量移除 → 原轨带 BGM。
- 处置：换 vocal 轨，重跑 02c 之后步骤（ops\08）；原发布库先完整备份；
  A/B 三段交用户耳朵定最终轨（P2）。

## 5. SOP 修订（已并入 ops\README.md §4.1）

02c linecut、片长帽 0.4–40s、asrScore 两类例外、BGM dropDb≥8 例外、
crosscheck 不传 initial_prompt、step04_asr 的 KEEP 正则含假名。

## 6. 仍属 P2（用户）

素材授权、抽听签字（10 行清单 + 新增 21/38）、对外发布、07 人格安装与切换。
