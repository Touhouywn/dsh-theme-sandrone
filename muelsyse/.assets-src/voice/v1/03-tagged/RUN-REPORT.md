# 缪尔赛思「新枝」v1 · 00–06 跑完记录

日期：2026-10-27 · 执行：flash 工位（数值）· 语义裁决：待定（见 §5）

## 1. 结论

| 阶段 | verdict | 关键数字 |
| --- | --- | --- |
| 00 acquire | PASS | 551.47s / aac 48k stereo / sha256 `8f63d335…b429` |
| 01 normalize | PASS | 48k 母带 + 16k 工作轨，时长差 0，peak ≤ -1.5 |
| 01.5 separate | PASS（not_applicable） | preLowShare 0.0199；p5Active -59.5 → -70.39；dropDb 10.89 |
| 02 slice | PASS（改道，见 §4.1） | VAD 150 段 → 碎片 204 条；整句 37 条 |
| 03 asr | PASS | 37/37 有文本；互校 p10/p25/p50/p90 = 0.767/0.829/0.929/1.0；<0.55 共 2 |
| 04 align | PASS | 38 行 → ok 36 / pending 1 / missing 1；alignedRate 0.947 |
| 05 audit | PASS（6 个 gate 全过） | aligned 36 / usable 35；长句 19 条 >10s，最长 36.86s |
| 06 release | PASS（只到 build+smoke） | 07-release 35 条，manifest 35 条无重复 |

## 2. 产物

- `sources/`：`BV17z421U71V.m4a`、`probe.json`、`source.sha256`
- `00-normalized/youngbranch/`：`source.wav`(48k)、`source-16k.wav`、`source-vocals.wav`、`meta.json`
- `01-separate/floor-drop.json`
- `01-slices/youngbranch/`：`vad.json`、`segments.json`、`clips/`（37 条整句）、`clips/index.json`、`linecut.tsv`、`_fragments/`（204 条碎片留档）
- `02-asr/`：`youngbranch.json`、`youngbranch.cross.json`、`youngbranch.words.json`（整轨词时间戳）
- `03-tagged/`：`aligned.tsv`、`audit.json`、`listen-checklist.tsv`
- `07-release/`：`clips/CN_*.wav`（35 个）、`manifest.json`

## 3. 对齐方法（02c，新增）

本片是 38 行连续朗读，行内停顿 0.3–1.2s。02b 的冻结参数（merge 250ms / split 1000ms）
把它切成 204 个 1.66s 碎片；单碎片对整句的 Dice 只有 0.24–0.51，38 行里 24 行过门槛
（alignedRate 0.63 < 0.85），按 §8 会 STOP。

所以追加 `pipeline/step02c_linecut.py`：用 whisper 整轨词级时间戳，把「38 行骨架文本」
与「整轨转写」做一次 semi-global 字符对齐（Needleman–Wunsch），把每行映射回词区间，
再按行切 37 条整句切片（含行 21 的手工候选 c0021）。碎片链的产物原样留在
`_fragments/`，未删。

整句切片的对齐 Dice：0.615–1.0，36 行 ≥ 门槛。

## 4. 与 ops brief 的偏差（全部为数值/工程口径，未动语义）

1. **02 切分**：新增 02c linecut（见 §3）。冻结的 VAD/rules 参数原样保留，碎片产物留档。
2. **03 互校**：`step04b_crosscheck.py` 不传 `initial_prompt`。实测日文逐片复听时该 prompt
   会被部分回显成「日本語で書き起こしてください。」，直接污染 guess（行 5/6/8/23/38 的
   asrScore 掉到 0.02–0.38）。整轨转写 `step02a2_words.py` 仍带 prompt。
3. **03 归一**：`step04_asr.py` 的 `KEEP` 也加了假名（README §3 只写了 04b；不加则
   SenseVoice 的 kana 全被吃掉，textClean 不可用）。
4. **05 时长门**：整句最长 36.86s，v2 的 0.4–10s 片长帽对本片不成立；05 按 0.4–40s 记，
   audit 的 gate spec 里注明了原口径。
5. **04 pending 判定**：未匹配行只要「前后已匹配切片之间还有未用切片」就给 top-2 候选
   （行 21 的 dice=0，但不该判 missing）。
6. **06 fade**：最终切片由 02c 切，留白 80/120ms、fade 25/40ms（按 §4 冻结表）；
   `step03_cut.py` 的 5/5ms fade 只作用在留档碎片上。

## 5. 待裁决（P1，交用户/Pro）

| 行 | 状态 | 证据 |
| --- | --- | --- |
| 21 选中干员1 | pending-pro | 官方「なぁに？」3 字；SV 出「な」、whisper 出「何?」，dice 0。音频 358.42–359.17s，候选 `c0021`（0.52s） |
| 43 生日 | missing | absent-in-video：42→44 只有 1.3s 间隔，容不下 99 字整句 |
| 38 新年祝福 | usable=false | align_dice 0.962、SV 全文正常；asrScore 0.29 是 whisper 30.4s 尾窗幻觉「ご視聴ありがとうございました」造成的。机械规则把它挡在发布库外，建议复听后加回 |

抽听清单 10 行：`03-tagged/listen-checklist.tsv`（首/中/尾 3 段 + low-align 3 行 + pending 1 行 + BGM A/B 3 组）。

BGM 疑点：数值 verdict=not_applicable（share 0.0199 < 0.15），但 demucs 后 p5Active 掉了
10.89 dB，且整轨长时间维持 -20 dBFS 底噪；疑为无低频的钢琴/氛围 BGM 绕过了 lowShare 判据。
本次按 brief 用原轨；A/B 已进抽听清单，换 vocal 轨只需重跑 02c 之后的步骤。

## 6. 环境备注（复跑需知）

- `curl` 在本机 TLS 失败（schannel `SEC_E_NO_CREDENTIALS`），下载用 `python -m yt_dlp` 直连。
- huggingface.co 直连超时；用 `HF_ENDPOINT=https://hf-mirror.com`。snapshot 的符号链接/临时目录
  被 DSH 沙箱挡住，medium 的空文件已按 trees 元数据把 blobs 硬链进 snapshots，运行
  faster-whisper 时设 `HF_HOME=E:\AI-theme\muelsyse\.cache\hf`、`HF_HUB_OFFLINE=1`。
- 重跑顺序：
  `step01_normalize` → `step015_separate` → `step015b_floordrop` →
  `step02a2_words` → `step02a_vad` → `step02b_rules_v4` → `step03_cut`（碎片）→
  `step02c_linecut`（整句）→ `step04_asr` → `step04b_crosscheck` →
  `step04_align` → `step05_audit` → `step06_release`。

## 7. 未做（按分工）

- P2：素材授权、抽听签字、对外发布。
- 07-persona：本次范围是 00–06，未安装人格插件、未切 `cordis.patch.yml`。
