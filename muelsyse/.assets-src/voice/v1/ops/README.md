# 缪尔赛思「新枝」语音库 v1 · 执行总纲

> 给 flash。只按本目录 brief 执行，不发挥。Pro（哥伦比娅）出 brief 与语义裁决（P1）；
> 数值裁决脚本自动（P0）；素材授权、抽听签字、发布归用户（P2）。
> 骨架参照 columbina v2（chain_v4 / RULES.md / ops 格式），复用其 pipeline 脚本，只做「路径 + 语言」改造。

## 1. 执行顺序

00-acquire → 01-normalize → 01.5-separate → 02-slice → 03-asr → 04-align → 05-audit → 06-release → 07-persona（人格，不依赖语音库，可随时做）→ 08-bgm-vocal-rerun（06 后若换 vocal 轨；含 Pro 三条裁决落地）

每阶段只读上一阶段产物，可单独重跑。每阶段结束写 `E:\AI-theme\muelsyse\.assets-src\voice\v1\state.json`
（{"stage","verdict","products","pending"}）。

## 2. 路径与环境（写死，勿改）

| 项 | 值 |
| --- | --- |
| ROOT | `E:\AI-theme\muelsyse\.assets-src\voice\v1` |
| 源键 | `youngbranch` |
| 源文件 | `ROOT\sources\BV17z421U71V.m4a` |
| 骨架 | `ROOT\skeleton-38.tsv`（Pro 已填，只读） |
| v2 参照 | `E:\AI-theme\columbina\.assets-src\voice\v2\pipeline\` |
| 捆绑 Python | `C:\Users\yuanshuifehe\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`（含 faster-whisper 1.2.1） |
| demucs 运行时 | `E:\AI-theme\columbina\.runtime\python310\python.exe`（torch cu121 + demucs 4.1.0） |
| ffmpeg | 捆绑 Python 下 `Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe` |
| voicekit | 不调 voicekit.cmd；用 voicekit venv python + `tools\voicepipe.py` + `_shim`（见 v2 common.py 的 voicekit()） |
| 代理 | `http://127.0.0.1:7892`（下载类失败时启用） |

## 3. 预备（只做一次）：复制 pipeline 并改四处

1. 复制 `columbina\.assets-src\voice\v2\pipeline\` 到 `ROOT\pipeline\`（含 `_shim\` 子目录）。
2. 改 `pipeline\common.py`：
   - `ROOT = Path(r"E:\AI-theme\muelsyse\.assets-src\voice\v1")`
   - `SOURCE_KEYS = {"youngbranch": ("BV17z421U71V", "【明日方舟·日文语音集·皮肤语音】缪尔赛思：新枝 Muelsyse: YOUNG BRANCH【CV. 田村由加莉】")}`
   - `PLUGIN` 行保留不动。
3. 改 `pipeline\step02a2_words.py`：`language="zh"` → `"ja"`；
   `PROMPT` → `"以下は日本語の音声です。日本語で書き起こしてください。"`；
   `WhisperModel("small", …)` → `WhisperModel("medium", …)`。
4. 改 `pipeline\step04b_crosscheck.py`：同上三处；另
   `KEEP = re.compile(r"[\u3040-\u30ff\u4e00-\u9fffA-Za-z0-9]")`（正则加入假名）。
5. 改 `pipeline\step015b_floordrop.py`：`KEYS = ["youngbranch"]`。

其它脚本一律不改。改完 state.json 记 `{"stage":"prepare","verdict":"PASS"}`。

## 4. 冻结参数（改动必须先改本文件）

| 项 | 值 |
| --- | --- |
| loudnorm | I=-18:TP=-1.5:LRA=11 |
| VAD | min_silence 200ms / merge 250ms / split 1000ms |
| 词帽 | 末词 end+60ms / 首词 start−40ms；能量端 40/50ms |
| 片长 | 0.4–10s；0.4–0.6s 标 filler；留白 80/120ms；fade 25/40ms |
| 可用 | asrScore ≥ 0.55；对齐入选 短(≤12字) 0.45 / 长 0.42；maxClips 2 |
| BGM 判定 | preLowShare ≥ 0.15 且 dropDb ≥ 3 → 用 vocal 轨 |
| whisper | medium int8 CPU；下载失败或单源超 30 分钟 → 退 small，并在 cross.json 注明 |

### 4.1 本片修订（语音集·连续朗读；2026-10-27 首跑后定稿，改参数先改本表）

| 项 | 修订 | 理由 |
| --- | --- | --- |
| 切分 | 行级整句用 `step02c_linecut.py`（whisper 整轨词时间戳 + 骨架文本 semi-global 对齐）；VAD/rules 碎片原样留档 `_fragments\` | 行内停顿 0.3–1.2s 击穿 merge 250 / split 1000，碎片对整句仅 24/38 过门槛 |
| 片长帽 | 行级 0.4–40s；碎片仍 0.4–10s | 本片 19 条 >10s，最长 36.86s |
| asrScore 例外 | <1s 短句（两引擎出子串碎片）与 >30s 长句（whisper 尾窗幻觉）不由互校拦行；Pro 凭 align_dice + 位置锚 + 单引擎全文裁决，note 记 pro-accepted | 行 21、38 已按此处理（见 PRO-VERDICT.md） |
| BGM 例外 | preLowShare < 0.15 但 dropDb ≥ 8 → 记 bgm-metric-suspect，A/B 抽听，可换 vocal 轨 | 非低频 BGM（钢琴/氛围）绕过低 share 判据；本片 dropDb 10.89 |
| crosscheck | 不传 `initial_prompt`（日文 prompt 会被回显进 guess 污染分数） | 行 5/6/8/23/38 实测 0.02–0.38 |
| 归一 | `step04_asr.py` 的 KEEP 正则同样要含假名 | 否则 SenseVoice 的 kana 全被吃，textClean 不可用 |

## 5. 语言差异（与 v2 的不同点，全部 ja）

- 主转写引擎不变：voicekit SenseVoice（自动检测，支持 ja）。
- 互校引擎 faster-whisper：language=ja、日文 PROMPT、medium。
- 归一正则必须含假名（见预备第 4 条）。
- 对齐对象是 38 行「新枝」官方文本（skeleton-38.tsv，来源 PRTS 语音记录页），不是 27 键意图。

## 6. 决策分级

| 级 | 判定者 | 示例 |
| --- | --- | --- |
| P0 数值 | 脚本自动 | 阈值、usable、missing、时长、静音、sha256 |
| P1 语义 | Pro（本会话） | 对齐存疑行（dice 低）、missing 行定性、模板段听感 |
| P2 权利/发布 | 用户 | 素材授权、抽听签字、发布 |

## 7. 回报格式（每阶段回一次，chat 不贴全量）

```
verdict: PASS|HOLD|STOP
changed: <文件列表>
diff: <≤10 行>
anomalies: <异常清单或 []>
reports: <报告文件路径>
```

## 8. if-then 降级总表

| 情况 | 动作（自动） |
| --- | --- |
| 下载器装不上 / 下载失败 | HOLD，贴错误；用户手动放 `sources\BV17z421U71V.m4a`（P2） |
| BGM verdict=fail | 用 vocal 轨但记 reason=bgm-fail；05 加抽 3 段 A/B 给 Pro |
| whisper medium 不可用 | 退 small，cross.json 记 model 字段 |
| usable 率 < 0.85 或 aligned 率 < 0.85 | 停，贴低分/缺失清单，Pro 重标定 |
| median < 0.6 或 P25 < 0.5 | HOLD，贴分位，Pro 重标定，不自动改阈值 |
| tailOverrun 非空 / 静音片 | 02 停，贴清单 |
| id 重复 / 骨架行数 ≠ 38 | 04 停，不写结果 |
| 发布 smoke 任一失败 | 用 backup 回滚，报 STOP |
