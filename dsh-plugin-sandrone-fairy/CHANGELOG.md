# 更新记录

## 1.0.1 — 放宽宿主版本门

- `engines.dsh` 从 `>=0.2.1-rc.3` 放宽到 `>=0.2.0`：修复 DSH 0.2.1-rc.2 宿主上被启动预检静默禁用的问题（代码只用稳定选择器与标准宿主服务，实测 rc.2 功能完好，不依赖 rc.3 专属接口）。

## 1.0.0 整合版 — 与工作台合并（sandrone-fairy 0.14.0 + 工作台整合改造）

把 0.8.0–0.14.0 的语音 / 控制台能力，与工作台 `dsh-theme-sandrone` 的接缝改造合并为一条「整合版」：

- **合作**：本版本与 B站 UP 主「是雪夕捏」合作完成。
- **皮肤**：`ui.skin` 默认 `workshop`（黑金，配合主题），`aurora`（深蓝紫）仍可切。
- **开屏**：`parts.splash=false` 默认——保留主题自带 16s 开屏，fairy 的 6.2s 电影开屏可配置开启。
- **语音**：`voice.mode=clips` 默认，只播 48 条预制台词；`auto` / `clone` 才实时合成，`off` 静音。`voice.engine` 默认 `api_v2`（本机零样本可出声），`lite`（GSV-TTS-Lite，需微调权重）可切，音色/风格解耦（`voice.timbre` / `poolSpeed`）、导演层 `[[emo=…]]` 四情绪池（cool/warm/tease/tired）不变。
- **称呼**：`voice.userName` 默认「你」。
- **路径**：Python / ffmpeg / 引擎定位环境变量化（`SANDRONE_PYTHON` / `SANDRONE_FFMPEG` / `SANDRONE_GS_API` / `SANDRONE_GS_REPO` / `SANDRONE_GS_PYTHON` / `SANDRONE_LITE_API` 等），无硬编码机器路径。
- **桌宠**：由「桑多涅工坊」插件开关控制。
- 新增能力随合并保留：可视化控制台 `/sandrone/ui`、安装自检 `/sandrone/setup`、档位降级 `/sandrone/tier`（A/B/C 按显存）、`/sandrone/voices`。
- 语音库 48 条预制 m4a 不变；微调权重（`Sandrone-e30.ckpt` + `sandrone4_e1_s128.pth`，330 MB）不在包内。

---

## 0.7.7 — 逐条精修（13 条）

按雪的逐条听感重烘 13 条，多数是「发音绕口 / 语速不对 / 情绪不对」，改法是改写台词 + 换参考音池 + 单独定语速：

| # | key | 改动 |
|---|---|---|
| 02 | welcome-back | 「我重泡一杯」→「我去换一杯」（避开 chóng/zhòng 两读），换 tease 池、0.98 |
| 03 | greet-morning | 加「呢」、尾字改「早啊」拉长，tease 0.95 |
| 05 | greet-afternoon | 拆短句，warm 0.95 |
| 12 | whisper-water | 缩到 8 字，tired 0.90 |
| 13 | react-hello | 改「来了。坐。茶还热着。」，cool 0.95 |
| 14 | react-thanks | 只放慢，tease 0.88 |
| 18 | react-tired | 去掉「推演我来跑」，tired 0.90 |
| 19 | react-night | 更轻更慢，tired 0.88 |
| 30 | react-morning | 三次迭代后定为「早。……我顺手泡的。不是特意等你。」，warm 0.95，**整体降 1 半音**（f0 273.5 → 258.5） |
| 31 | react-wake | 补厌倦感「再躺三十秒，别叫我」，tired 0.88 |
| 32 | react-goodnight | 放慢，tired 0.88 |
| 41 | idle-noon | 改写语序，cool 0.92 |
| 48 | farewell | 补一句「回头见」，warm 0.95 |

- 新增工具：`tools/polish.py`（批量候选 + 五维体检）、`tools/apply_clip.py`（单条套增益参数落盘）、`tools/retune.py`（一次改文本/池/语速并同步三处）。
- `client.js` 的 `GREET_TEXT` 与 `REACTIONS` 文案已随台词同步，避免字幕与音频不一致。

## 0.14.0 — 开源整理

- README 重写：四部件说明、语音四层原理、安装（Windows / Linux / macOS）、配置表、运行档位、台词分组、路由表、常见问题、授权边界。
- 新增 `install.sh`（Linux / macOS，与 `install.ps1` 行为一致：复制 + 软链 + 幂等追加 patch 行 + 剥 BOM；`--purge` 卸载）。
- 新增 `tts/requirements.txt`（含 cu121 提示），自检页缺依赖时照着装即可。
- 截图归到 `docs/img/`，README 直接引用；打包脚本把 `docs/` 与 `install.sh` 纳入，并排除 `tts/source.wav`、`jieba.cache` 这类大件。
- 包体：149 文件 / 17.86 MB（不含底座模型 1.28 GB、不含训练权重 330 MB）。

## 0.13.0 — 按机器能力自动降级

- 新增 `GET /sandrone/tier`：读 `nvidia-smi` 的显存，把机器分成三档，并给出该档的语音参数（缓存 5 分钟）。
  - **A** 显存 ≥3 GB：Lite + 流式，念 2 句 / 58 字
  - **B** 显存 1.5–3 GB：Lite 非流式（省显存尖峰），2 句 / 40 字
  - **C** 无独显或显存 <1.5 GB：Lite 走 CPU，只念 1 句 / 24 字
- 客户端按档位收紧：`VOICE_CAP` / `VOICE_PIECES` 从档位读，档位 `stream=false` 时把 `SPEAKER.streamOn` 关掉，退回「整句合成再播」。
- 控制台与自检页都显示当前档位与判定理由（例如「A · GPU 充裕｜显存 4096 MB，够跑流式」）。
- 调试参数：`/sandrone/tier?tier=B` 或 `?vram=1200` 可直接模拟低配，方便给别人演示或截图。
- 实测本机：`tier=A / 4096 MB / stream=true / caps=2×58`。

## 0.12.0 — 安装自检页

- 新增 `GET /sandrone/setup`：一条一条列「宿主 / Python 环境 / 底座模型 / 声模权重 / 情绪参考音 / ffmpeg / 显卡 / 预制台词 / Lite 服务 / api_v2 服务」，每项给状态、原因、可复制的修复命令。
- 新增 `GET /sandrone/setup/check`：服务端实际探测（`find_spec` 判 gsv_tts，避免 import torch 冷启动 20 秒把探测拖超时；`nvidia-smi` 读显卡名与显存；目录体积统计模型是否下全）。
- 新增 `POST /sandrone/setup/start`：`{"target":"lite"}` 直接拉起推理服务并等它就绪（最多 60 秒），`api_v2` 同理。
- 页面上有「重新检测 / 启动 Lite 服务 / 打开控制台 / 回到 DSH」；修复命令一键复制。控制台页也加了「安装自检」入口。
- 修掉一启动失败就静默退出的问题：子进程继承的 `TEMP` 可能是不可写路径，Python `tempfile` 会直接 `FileNotFoundError: No usable temporary directory` 整进程退出。现在拉起时强制 `TEMP/TMP/TMPDIR=data/tmp/`，并把子进程 stdout/stderr 落到 `data/lite.log`，`/sandrone/setup/start` 失败时回传日志尾巴。
- 实测：宿主内一键拉起 → **23 秒就绪**，随后 `/sandrone/tts` 2.08s 返回 87KB wav。
- 判断逻辑：红=必须修（缺 Python 环境、缺权重、缺参考音、缺台词），黄=能跑但缺功能（ffmpeg、显卡、推理服务未启动）。

## 0.11.0 — 情绪平滑、人设校验、控制台

- **情绪历史平滑**：模型每轮独立投票会出现跳变。新增 `EMO_ADJ` 邻接表——相邻档（cool↔warm↔tease）可直接切；`tired` 只能从 warm/tired 进入且要连续两轮同票才升级。`{t:'emo'}` 事件补 `want`（模型原始投票）与 `held`（被压住的票），便于排查。
- **人设校验（确定性规则）**：客户端对每句做两道正则——越权承诺（「我帮你改/删/跑/执行…」）与甜腻低幼词（人家/宝宝/亲亲/抱抱/喵…）。命中就**不让这句出声**，文字照常显示，并写一条 `console.warn`。不依赖模型自觉。
- **可视化控制台** `GET /sandrone/ui`：运行状态（引擎/音色/推理服务/显存/台词条数）、部件开关、语音参数（引擎/音色/称呼/温度/按池调速/空闲退出/唤醒超时）、桌宠（形象/尺寸/停靠角）、四池试听、整份配置 JSON 直改。面板头部新增齿轮按钮一键打开。
- **`GET /sandrone/voices`**：回 `tts/pack.json` 的 key/正文，供控制台与外部工具统计。
- 深蓝紫配色，与插件面板同一套视觉语言；纯静态 HTML，无构建、无依赖。

## 0.10.0 — 导演层、按轮锁、风格收窄

- **导演层**：system prompt 追加 `DIRECTOR_RULES`，要求回复首行输出 `[[emo=cool|warm|tease|tired]]`；宿主用 `stripEmotionTag()` 逐块剥离（带缓冲，支持任意切分），匹配到即发 `{t:'emo'}` 事件，正文里不留痕迹。
- **按轮锁**：客户端收到 `emo` 后设 `SPEAKER.lockPool`，本轮所有句子都用这个池合成；`/sandrone/tts` 接受 `pool` 覆盖逐句判定。每轮开始清空，模型不给标签就退回逐句 `pickPool`。
- **风格收窄**（按「微小变动、可识别即可」）：四池语速 0.95/0.92/0.98/0.90 → 0.96/0.95/0.97/0.94；`tease` 的参考音从 `ref-vivid.wav` 换成 `ref-warm.wav`（去掉最跳的一把）。
- **随机性收敛**：Lite 的 GPT 采样默认 `temperature=1.0` 会让同一句时长在 2.3–3.2s 间漂移；新增 `voice.temperature`（默认 0.7，clamp 0.3–1.2）透传到 `/infer` 与 `/stream`，四池同句时长收敛到 1.87–2.56s。
- 实测（同句「雪，茶凉了，我去换一杯。」，temperature 0.7）：cool 1.87s / warm 2.56s / tease 2.39s / tired 2.00s。
- 试听：`preview/gsv-lite/styles-四池对比.m4a`（cool → warm → tease → tired，句间 0.45s）。

## 0.9.0 — 音色与风格解耦

- Lite 服务端把「音色（谁在说）」与「风格（怎么念）」拆成两个独立参数：`/infer {"text","pool","timbre","speed"}`。音色注册表 `TIMBRES`（默认 `sandrone`，另备 `alt-a`/`alt-b` 两条原声），风格仍是四池 `cool/warm/tease/tired`。
- 配置项新增 `voice.timbre`（默认 `sandrone`）与 `voice.poolSpeed`（默认 true，Lite 逐句套用各池语速 0.90–0.98），`/sandrone/voice` 会回报当前音色。
- 实测（同一句「雪，茶凉了，我去换一杯。」）：

  | 风格 | 时长 | f0 中位 | f0 标准差 |
  |---|---|---|---|
  | cool | 1.92 s | 251.0 Hz | 54.2 |
  | warm | 2.40 s | 264.5 Hz | 44.6 |
  | tease | 1.96 s | 255.0 Hz | 47.9 |
  | tired | 1.67 s | 249.0 Hz | 60.5 |

- 声纹验证（模型自带 ERes2Net）：跨风格 0.79–0.91（均值 0.879），与「同一人不同录音」的 0.88 同量级 → **换风格不会把音色带跑**；换音色（line4 ↔ line3，同为桑多涅原声）也是 0.86–0.90，说明两个备选音色确实还是她本人。
- 新增 `tools/gsv_lite_decouple.py`（2 音色 × 4 风格矩阵，出 `preview/gsv-lite/decouple/report.json`）与四池对比试听 `preview/gsv-lite/styles-四池对比.m4a`。
- 服务端新增 `POST /verify {"a","b"}`，用模型自带的声纹模型直接给两段音频打分（`always_load_sv=True`，显存 +0.1 GB）。

## 0.8.0 — 双引擎：api_v2 / lite 可切换

- 新增第二套推理引擎 **GSV-TTS-Lite**（`tts/gsv_lite_server.py`，常驻 HTTP 服务，默认 9882 端口），与本地的 api_v2 共用同一套 GPT/SoVITS 权重，音色完全一致。
- 配置项 `voice.engine`：`api_v2`（默认）| `lite`。切换只改配置，不重装：
  `POST /sandrone/config {"voice":{"engine":"lite"}}`，刷新页面生效。
- 实测对比（同一句、RTX 3050 Laptop 4GB）：

  | 指标 | api_v2 | lite |
  |---|---|---|
  | 流式首字节 | 0.61 s | **0.21–0.38 s** |
  | 整句耗时（约 2.4 s 音频） | 2.3 s | **0.5–0.7 s** |
  | 非流式单句 | 2.2–2.5 s | **1.4 s** |
  | 显存峰值 | 2.7 GB | **1.2 GB** |
  | 模型加载 | 16–20 s | 11.5 s |

- 修掉两个上游坑（都写进 `tts/gsv_lite_server.py` 注释）：
  1. `langid` 会把「语音回路已接通」判成吴语 `wuu`，LangSegment 白名单只有 zh/en/ja/ko，**整段被静默丢弃**——现在把中文族标签统一折算成 zh，任意输入都不掉字。
  2. CUDA Graph 捕获期间 cuDNN 的 SDPA 会报 `operation not permitted`，服务端启动即把后端固定为 `EFFICIENT_ATTENTION`。
- 流式响度对齐：Lite 原始 PCM 峰值只有 ~0.20（我们烘好的台词是 ~0.83），流式又不能过 ffmpeg，因此宿主转发时按 `SANDRONE_LITE_GAIN`（默认 4）做增益 + 削波，实测流式峰值从 −13.9 dB 提到 −1.6 dB，与非流式一致。
- 低配机器：Lite 显存占用只有 api_v2 的 44%，可在 4GB 卡上与 DSH 共存；CPU 也能跑（慢 3–4 倍），文档给了降级顺序。

## 0.7.6 — 语音库加厚与两处听感修整

- 预制台词 **28 → 48 条**：新增 20 条反应台词（早安/晚安/刚醒/加班/吃饭/久坐/生病/难过/道歉/失败/成功/想放弃/该休息/灯光/同意/疑惑/差不多/被夸/没空/收工），全部按池烘好。
- `REACTIONS` 规则 **6 → 24 条**，按「更具体的先匹配」排序，避免「晚安」被「累了」之类的宽泛规则抢走。
- 修整 10 条听感偏的句子（6 条起伏过大、4 条偏平）：换参考音 + 微调语速重焙，产出 `preview/ab-fix/AB-旧-新-交替.m4a` 供对比。
- 新增 `tools/clip_report.py`（逐条量 f0 标准差/跨度/能量/高频）、`tools/ab_fix.py`（A/B 候选烘焙）、`tools/ab_seq.py`（拼对比音频）、`tools/voice_sheet.py`（连播 + 点播清单）。

## 0.7.5 — 代码自检与配置接线

- 修复 `streamOn` 从未被赋值（流式判断恒真），改为构造时显式 `true`。
- 配置项真正生效：`splash.skipMs`（开屏时长与三个计时点全部按它推导）、`splash.greeting`（关掉就不念「欢迎回来」）、`pet.size`（桌宠尺寸上限 160–560）、`voice.idleMs` / `voice.wakeMs`（引擎空闲卸载与唤醒等待，`POST /sandrone/config` 即时生效，启动时也会应用一次）。
- 移除从未接线的 `pet.panel`（面板按设计固定右上角，留这个开关只会误导）。
- `stop()` 现在会掐掉已排进 AudioContext 时间轴的预制台词，不再出现「点了停声还在念」。

## 0.7.4

- 主动开口这件事收紧到「不该吵」的程度：
  - 检查间隔 24 秒 → **15 分钟**，单次放行概率 50% → **30%**。
  - 两条主动台词之间强制间隔 2.5 分钟 → **10 分钟**。
  - `idle-long`（你安静了挺久）阈值 8 分钟 → **45 分钟**，优先级仍是 45%。
  - `welcome-back`（回来了）阈值 30 分钟 → **2.5 小时**。

## 0.7.3

- 再加 6 条**不需要你开口**的时段台词（共 28 条）：`idle-dawn`（05–08）、`idle-noon`（11–13）、`idle-afternoon`（13–17）、`idle-dusk`（17–21）、`idle-late`（23–05）、`idle-long`（你安静超过 8 分钟）与 `welcome-back`（离开 30 分钟以上回来）。
- 挑选规则：`AMBIENT` 表按时段给权重，60% 走时段台词、40% 走通用低语；`idle-long` 在长时间无交互时占 45% 优先级；两条主动台词之间强制间隔 2.5 分钟，避免刷屏。
- `welcome-back` 在开屏结束、进面板那一刻播；`localStorage` 里记 `seenAt` 判断离开了多久。

## 0.7.2

- 新增 8 条预制台词（共 22 条），覆盖日常场景：`react-hello`（来了/我回来了）、`react-thanks`（谢谢）、`react-tired`（累了）、`react-night`（晚安）、`react-done`（做完了）、`react-error`（断线）、`react-praise`（被夸）、`idle-late`（深夜低语）。
- 场景反应会**排在回复语音前面**播：`SPEAKER.sayReaction()` 把预制音频排进同一条 AudioContext 时间轴（`beginClip`），所以文字、反应音、回复音三者的先后是确定的，不会叠在一起。
- 深夜（23:00 后）的空闲低语有 50% 概率换成 `idle-late`；请求失败时会接一句 `react-error`。
- 修掉队列竞态：`pumpQueue` 收尾瞬间新入队的句子可能一直躺在队列里（现在收尾会补一次检查）。

## 0.7.1

- 台词不再硬编码称呼：`greet-morning`、`greet-evening`、`whisper-water`、`voice-demo` 四条重新录制，句子里不再出现「雪」，任何用户都能直接用。
- 称呼改成可配置：配置项 `voice.userName`（默认 `雪`），也可用环境变量 `SANDRONE_USER_NAME`；只影响界面标签与提示词，不影响音频。
- 人格提示词里的固定称呼改为占位符渲染（`personaFor(name)`），`buildMessages()` 也带上当前称呼。

## 0.7.0

- **流式播放**：宿主 `/sandrone/tts` 支持 `{"stream": true}`，用 GPT-SoVITS 的
  `streaming_mode=3 + media_type=raw` 把 int16 PCM（32k 单声道）原样透传；
  浏览器侧改用 Web Audio 分块调度，**首块约 0.6–0.7s 就出声**（原来要等整句合成完，约 2.5–3s）。
  整句合成仍是回落路径：流式失败自动退回 `audio/wav` + `Audio`，用户听不到差别。
- **同一句稳定**：请求带确定性种子 `seed = FNV1a(pool + 文本)`，`temperature 0.95`、`top_p 0.95`、
  `top_k 15`、`repetition_penalty 1.35` 全部显式固定。同一句连打两次输出字节完全一致（此前会换念法）。
- **开头不再有启动噪声**：预制台词补上 `silenceremove(-45dB) → 15ms 淡入 → 60ms 前置静音 → loudnorm`，
  实测开头 0.1s 的 HF 占比从 55.2% 降到 12.3%、电平从 -55.7 dBFS 升到 -16.0 dBFS。
- AudioContext 在「点她」这一下预建（浏览器要求手势），避免第一次流式播放被拦截。
- 新增 `tools/test_stream.mjs`：用假 AudioContext 在 Node 里跑通 `SPEAKER.speakStream`，
  断言首块少于 1.5s、调度块数大于 1。

## 0.6.0

- 语音参考音从「三档气质（vivid/warm/soft）」改为「四个情绪池（冷 / 温 / 讽 / 倦）」，
  `pickPool()` 按句内用词 + 时段选池，深夜（23:00–05:00）固定走「倦」。
- 缓存键修正：现在包含池名 + 参考音原文 + 语速 + 文本，换权重或换参考音不会再回放旧音频。
- `GET /sandrone/voice` 的 `refTiers` 改为 `pools`，回传每个池的参考音、原文与语速。
- 试验记录：曾用 128 条语料里 3.2–8 秒、带准确原文的片段做四池参考音（配 `prompt_text`），
  实测 13/14 句音高幅度下降 20–30%，故回退为「按韵律起伏筛出的 5.6 秒窗口」。
  详见 `tools/pick_pool_refs.py`、`tools/prompt_text_ab2.py`、`tools/prosody_report.py`。

## 0.5.0 — 2026-10-26 · 整合

把开屏、桌宠、语音三块收进一个可配置的 bundle，接缝对齐合作者的 `dsh-theme-sandrone`。

**新增**

- `parts` 开关：`splash` / `pet` / `voice` 三块可独立关闭，配置落在 `data/config.json`。
- HTTP 配置路由 `GET/POST /sandrone/config`（深合并、持久化、坏 JSON 回 400）。
- 桌宠角落可配：`pet.corner = bottom-left | bottom-right`，气泡自动换边。
- `voice.mode` 三态：`auto`（跟随作息）/ `clone`（锁原声）/ `off`（静音）。
- `GET /sandrone/voice` 自检字段补齐：`child` / `spawnedAt` / `idleMs` / `python`。
- `README.md`、`CHANGELOG.md`、`NOTICE.md`、`LICENSE`、`install.ps1` / `uninstall.ps1`、`tools/smoke.mjs`。

**变更**

- 桌宠默认停靠改到**左下角**（原本右下），面板固定在**右上角**（原本贴右下）。
- 语音服务改为**按需唤醒**：启动不预热，首次说话才拉起，空闲 8 分钟自动卸载；实测冷启动 37.4s、热态 2.9s、同句缓存 0.03s。
- `package.json` 升到 0.5.0：补 `license` / `main` / `engines.dsh` / `keywords`，`files` 收全。

**修复**

- `ensureGsServer()` 调用了已经不存在的 `clonePickPython()`（上一代 CosyVoice 的遗物），`ReferenceError` 被 catch 吞掉，导致首次说话永远 502。改用 `gsPython()`：内置运行时 → `SANDRONE_PYTHON` → PATH。
- 开屏/桌宠此前会先渲染一帧再读配置；现在 `stage = 'boot'`，配置到手才决定播不播，避免闪一下。

---

## 0.4.x — 语音与立绘迭代（此前的连续改动）

- 原声从 CosyVoice2 零样本换成用户自训的 GPT-SoVITS v2ProPlus（`sandrone4_e1_s128.pth`），用 128 段 / 328.5 秒语料微调。
- 立绘改用官方 2048×2048 带 alpha 原画，整张不裁边，机偶容器改 1:1。
- 文字与语音严格对齐：句子要等 `audio.play()` 成功才显示。
- 开屏问候重焙到 0.92 语速（5.90s），时间轴 3900 / 6400 / 7600 ms。
- 音量统一 loudnorm（−14 LUFS / TP −1.5）；固定台词离线重制 14 条。

## 0.3.x

- 开屏电影化：`sdf-cine` 六秒镜头（特写 → 横移 → 全景）+ 立绘弹入。
- 玻璃拟态对话面板、流式逐句播放、低语气泡、拖拽记忆。

## 0.2.x

- 首次跑通 `/sandrone/chat`：`ctx.llm.stream()` + NDJSON；修 StreamChunk 判别字段是 `type` 不是 `kind`。

## 0.1.x

- 从模板 `decoration` 起手：`shell.overlay` 注册、静态资源路由、`speechSynthesis` 兜底。
