# 交接说明 · sandrone-fairy 0.14.0 整合版

这套是「开屏动画 + 桌宠 + 语音 + 控制台」的整合包，0.14.0 起已与你的 `dsh-theme-sandrone` 完成工作台合并：**你负责背景与配色，这套负责开屏、桌宠、语音与控制台**。默认皮肤切到黑金 `workshop`、开屏让给主题（fairy 的 6.2s 电影开屏可配置开启）、语音默认只播 48 条预制台词（`voice.mode=clips`）。下面按「包里有什么 / 怎么装 / 怎么和你的包对接」写清楚。

---

## 一、包里有什么

```
sandrone-fairy/
├─ package.json          # dsh.bundle.patch + dsh.client（platform: web, immediately）
├─ index.js              # 宿主半边：/sandrone/{config,ping,chat,tts,voice,asset}
├─ client.js             # 浏览器半边：开屏 / 桌宠 / 对话面板 / 语音播放
├─ cordis.patch.yml      # 一行 insert：id: sandrone-fairy
├─ icon.svg              # 原创手绘（不含官方图形）
├─ locale/{zh,en}.json   # meta.title / meta.description
├─ assets/
│   ├─ figure.png        # 立绘（2048²，带 alpha，整张不裁）
│   ├─ cine.jpg          # 开屏原画（2560 宽）
│   └─ voice/*.m4a       # 14 条固定台词（开屏问候、时段问候、低语、思考、告别）
├─ tts/                  # 语音脚本（不含模型）
│   ├─ gs_api.py         # GPT-SoVITS 的启动器（给 api_v2.py 打 langdetect 补丁）
│   ├─ pack_gs.py        # 把台词表烘成 m4a（loudnorm + aac 128k）
│   ├─ remaster.py       # 已有 m4a 的批量增益（loudnorm -14 LUFS）
│   ├─ use_weights.py    # 切换 SoVITS 权重并重启服务
│   ├─ build_dataset*.py / train.py / ab_test.py / audition.py  # 语料、微调、A/B
│   ├─ pack.json         # 台词表（和 voice/*.m4a 一一对应，改台词两边都要改）
│   ├─ ref/line1..6.wav  # 早期参考音（6 段原声，各 5–7 秒，保留备查）
│   ├─ ref/ref-{vivid,warm,soft}.wav  # 现在用的三档参考音（见下）
│   └─ make_refs.py      # 从原声长音轨自动挑三档参考音
├─ tools/smoke.mjs       # 打四个路由的自检脚本
├─ install.ps1 / uninstall.ps1
└─ README / CHANGELOG / NOTICE / LICENSE
```

**没有放进去的**（体积或隐私原因）：

| 东西 | 为什么 | 你那边怎么补 |
| --- | --- | --- |
| `tts/gptsovits/`（约 1.3 GB） | GPT-SoVITS 引擎 + 底座权重 | 见下面「二、语音引擎」 |
| `data/config.json` | 我的运行时配置（部件开关、停靠角） | 首次运行自动生成默认值 |
| `assets/voice/cache/` | 我合成过的句子缓存 | 留了空目录 |
| `tts/dataset*`、`tts/source.wav` | 训练语料（约 330 秒切分 + 28 MB 原始音频） | `build_dataset2.py` 可重新切 |
| `preview/` 的视频管线与截图 | 不属于运行时 | 只留了开屏/面板两张成品图，供 README 引用 |

---

## 一点五、参考音分档（0.5.2 新增）

同一句话，**换参考音就会换底色**，这是不改模型就能做情绪分层的最便宜的办法：

| 档位 | 参考音 | 语速 | 什么时候用 |
| --- | --- | --- | --- |
| `vivid` | `tts/ref/ref-vivid.wav` | 1.00 | 傲娇、抢话、短促（如「哼，才不等你呢。」） |
| `warm` | `tts/ref/ref-warm.wav` | 0.95 | 日常、解释、陪伴（默认档） |
| `soft` | `tts/ref/ref-soft.wav` | 0.90 | 深夜、低语、哄（23:00–05:00 强制走这档） |

- 实时回复：`index.js` 的 `pickTier(text, hour)` 按关键词 + 时段判定，缓存 key 里带档位，换档不会命中旧缓存。
- 固定台词：`tts/pack_gs.py` 的 `TIER_OF` 里手排（14 句）。
- 三档参考音由 `tts/make_refs.py` 从 25 分钟原声里按「响度 / 谱平坦度 / 过零率 / 浊音稳定度」自动挑出，不需要人工试听。

改这三条参考音要重焙台词：`python tts/pack_gs.py`（约 15 分钟 GPU，14 条）。

---

## 一点六、桌宠形象（0.5.3 新增）

`assets/` 下四套立绘，配置项 `pet.model`：

| 值 | 文件 | 样子 |
| --- | --- | --- |
| `classic` | `figure.png` | 原立绘（默认） |
| `sit` | `figure-sit.png` | 侧坐、端着茶杯 |
| `cake` | `figure-cake.png` | Q 版、举着草莓蛋糕 |
| `pout` | `figure-pout.png` | 嘟嘴大头 |

切换入口在面板右上角的人形图标（点一下循环），或直接 `POST /sandrone/config {"pet":{"model":"cake"}}`。四张图都走 `/sandrone/asset/*`，要换成自己的图，保持文件名或改 `client.js` 里的 `PET_MODELS` 即可。

---

## 一点七、四个情绪池（0.6.0 起）

参考音从「三档气质」改为「冷 / 温 / 讽 / 倦」四个池，`pickPool()` 按句内用词 + 时段选池
（23:00–05:00 固定「倦」）。四条参考音都在 `tts/ref/ref-*.wav`，各 3–6 秒。

**换参考音的硬要求**：3–10 秒，且最好配上它的准确原文（`prompt_text`）。
实测：空 `prompt_text` 只锁音色，韵律会平；但用「语义贴、韵律平」的短片段当参考音，
13/14 句音高幅度反而降 20–30%（已回退）。结论——参考音优先选**韵律起伏大**的片段，
语义贴合是第二位的。

## 二、语音引擎（唯一需要你动手的部分）

实时对话用 **GPT-SoVITS v2ProPlus**，通过本地 HTTP 调（默认 `http://127.0.0.1:9880`）。插件**不会**启动时预热它：第一次要说话才拉起，空闲 8 分钟自动 `taskkill`（实测冷启动 30–37 s，热态 2.9 s，同句缓存 30 ms）。

放引擎到 `tts/gptsovits/` 后，需要两份权重：

```
tts/gptsovits/GPT_weights_v2ProPlus/Sandrone-e30.ckpt          # GPT 半边（148 MB）
tts/gptsovits/GPT_SoVITS/SoVITS_weights_v2ProPlus/sandrone4_e1_s128.pth   # SoVITS 半边（165 MB）
```

然后：

```powershell
# 1) 底座（ModelScope，约 1.24 GB）→ 复制进 GPT_SoVITS/pretrained_models/
#    s1v3.ckpt / v2Pro/s2Gv2ProPlus.pth / sv/pretrained_eres2netv2w24s4ep4.ckpt
#    chinese-hubert-base/  chinese-roberta-wwm-ext-large/
# 2) python 依赖：torch cu121、modelscope、ffmpeg-python、resampy、tensorboard、zhconv
# 3) 指向权重并起服务
python tts/use_weights.py e1
```

几个**必须知道**的坑（我踩过，省你时间）：

- `import jieba_fast` 在 py3.12/Windows 编不出 wheel → 在 site-packages 里放一个 shim 包转发 `jieba`。
- `fast-langdetect` 离线不可用 → `gs_api.py` 里已经把 `detect` 固定成 `zh`，别绕过它直接跑 `api_v2.py`。
- 健康探针别用 `GET /tts`（会 500）；用 `GET /openapi.json` 且只判 `status < 500`。
- 服务必须用 `Start-Process -WindowStyle Hidden` 或 `spawn(detached)` 起；用 PowerShell 管道接 `Tee-Object | Select-Object -First N` 会在 N 行后把服务端杀掉。

> 想换成你自己的引擎（云端 TTS、你自己的推理服务）也很容易：`client.js` 只认「Blob → Audio」，在 `index.js` 的 `synthClone()` 旁边加一个同签名的 `synthRemote()`，再把 `voice.mode` 加一个取值即可。

---

## 三、怎么装

```powershell
# 方式 A：DSH 插件管理器
plugin_manager install_bundle  target = <这个目录的绝对路径>

# 方式 B：脚本（复制 + junction + 幂等追加 patch 行 + 剥 BOM）
pwsh -File .\install.ps1
pwsh -File .\install.ps1 -WithEngine     # 引擎一起复制
pwsh -File .\uninstall.ps1               # 只摘掉 patch 行与链接，文件保留
```

装完**刷新页面**。改了宿主半边（`index.js`）要重挂载：`set_plugin {target:'include:sandrone-fairy', enabled:false}` → `enabled:true`；浏览器半边（`client.js`）刷新即生效。

自检：

```powershell
node tools\smoke.mjs            # 自动找端口
node tools\smoke.mjs 54306      # 或指定
```

---

## 四、配置（运行时，不用改代码）

`data/config.json`，HTTP 读写（POST 是深合并，只传要改的字段）：

```bash
curl http://127.0.0.1:<端口>/sandrone/config
curl -X POST http://127.0.0.1:<端口>/sandrone/config -H "content-type: application/json" \
     -d '{"parts":{"splash":false},"pet":{"corner":"bottom-right"},"voice":{"mode":"off"}}'
```

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `parts.splash` | `false` | 开屏开关——整合版默认关，由主题 16s 开屏接管；开启后播 fairy 6.2s 电影开屏 |
| `parts.pet` / `parts.voice` | 全 `true` | 桌宠 / 语音，可独立关掉（控制台是 `/sandrone/ui` 静态页，不在 `parts` 内） |
| `splash.everyLoad` | `true` | `false` = 刷新不播 |
| `splash.skipMs` | `7600` | 开屏时长（点击/任意键可跳过） |
| `pet.corner` | `bottom-left` | `bottom-left` / `bottom-right`，气泡自动换边 |
| `voice.mode` | `clips` | `clips`（只播 48 条预制台词）/ `auto`（跟随作息：23:00–05:00 静音、周末假日原声）/ `clone`（锁原声）/ `off`（静音） |
| `voice.engine` | `api_v2` | `api_v2`（兼容旧链路，本机零样本可出声）/ `lite`（GSV-TTS-Lite，需微调权重） |
| `ui.skin` | `workshop` | `workshop`（黑金，配合主题）/ `aurora`（深蓝紫） |

---

## 五、和你的包对接（整合版接缝）

整合版已经把这些接缝焊死，下面是合并后的最终约定：

1. **皮肤** — `ui.skin=workshop`（默认）就是你这套的黑金，我保留 `aurora`（深蓝紫）作为可切皮肤。面板 / 开屏内部配色随 `ui.skin` 走，不再各自为政。
2. **自定义背景** — 背景归你（`/theme-sandrone/background.webp` 铺右侧 + 左侧渐变遮罩），我这套的开屏原画只在 `splash` 层，**不碰应用画布**。若想让开屏也用你的图，加一个 `splash.art` 字段指过去即可，`client.js` 里只是一处 `<img src>`。
3. **开屏** — `parts.splash=false`（默认）时，开屏完全让给你的主题 16s 开屏；需要 fairy 的 6.2s 电影开屏时把 `parts.splash` 打开即可，两者不叠加。
4. **桌宠** — 我独占 `shell.overlay` 的 `bottom-left`（`order: 60`），面板钉 `top-right`；桌宠整体由「桑多涅工坊」插件的开关控制。`pet.corner` 已支持右上/右下。
5. **语音** — `voice.mode=clips`（默认）只播 48 条预制台词，不拉引擎；切 `auto` / `clone` 才按 `voice.engine` 实时合成。客户端不关心谁合成的，加一个引擎取值即可。

**路径不再硬编码**：Python / ffmpeg / 引擎定位全部环境变量化——`SANDRONE_PYTHON` / `SANDRONE_FFMPEG` / `SANDRONE_GS_API` / `SANDRONE_GS_REPO` / `SANDRONE_GS_PYTHON` / `SANDRONE_LITE_API` 等，未设置时按「内置运行时 → PATH」回退。换机器不用改代码，只需设这几个变量。

---

## 六、接口一览

| 路由 | 方法 | 用途 |
| --- | --- | --- |
| `/sandrone/config` | GET / POST | 上面那张表 |
| `/sandrone/ping` | GET | 默认模型是否可用 |
| `/sandrone/voice` | GET | 只读自检（**不会**唤醒服务） |
| `/sandrone/chat` | POST | NDJSON 流式回复 |
| `/sandrone/tts` | POST | 合成一句 → `audio/wav`（带 `x-sandrone-voice` 头） |
| `/sandrone/asset/…` | GET | 立绘、开屏原画、台词 m4a、缓存 |

`/sandrone/asset` 是 **prefix** 路由，注册时**不能带结尾斜杠**（带了永不匹配）。

---

## 七、已知限制

- 冷启动 30–37 s 不出声（按需唤醒的代价）；想更快就调大 `SANDRONE_GS_IDLE_MS` 或改成常驻。
- 4 GB 显存以下要靠 `n_timesteps=8` + half 才跑得动；显存更宽裕可以调高换质量。
- 只在 Windows 桌面端验证（PowerShell 7 + DSH 内置 python 运行时）。
- 素材版权见 `NOTICE.md`：立绘/原画/语音属于米哈游与配音演员，仅个人使用。

## 一点八、流式播放（0.7.0）

- `POST /sandrone/tts` 接受 `{"stream": true}`，响应头 `content-type: audio/L16;rate=32000;channels=1`，
  body 是**上游直接透传的 int16 PCM**（GPT-SoVITS `streaming_mode=3` + `media_type=raw`）。
- 浏览器侧用 Web Audio 分块调度（`SPEAKER.speakStream`），**首块约 0.6–0.7s 出声**；
  失败自动回落到整句 `audio/wav` + `Audio`，两条路现象一致。
- 流式不做 ffmpeg 后处理、不写缓存（要压就变成等整句）；需要音量/掐头时走非流式那条。
- 同一句稳定：请求带 `seed = FNV1a(pool + text)`，`temperature 0.95` / `top_p 0.95` / `top_k 15` 固定。
- 自测：`node tools/test_stream.mjs`（假 AudioContext，断言首块 <1.5s、调度块 >1）。

---

## 一点九、称呼与去昵称

0.7.1 起，预制台词里**不再出现任何称呼**，发给别人也能直接用。

- 文字层称呼由 `voice.userName` 控制（默认 `雪`），也可用环境变量 `SANDRONE_USER_NAME`。
- 改法：`POST /sandrone/config {"voice":{"userName":"你"}}`，或直接改 `data/config.json`。
- 音频不读这个名字：想换称呼不需要重焙台词。

---

## 二、预制台词的扩展方式

`assets/voice/*.m4a` 现在有 22 条，分 `welcome` / `greet-*` / `whisper-*` / `react-*` / `idle-late` 五组。

- 加台词：`tts/pack.json` 加一行 `"键名": "文本"`，在 `tts/pack_gs.py` 的 `POOL_OF` 里指定情绪池，然后 `SANDRONE_ONLY=键名 python tts/pack_gs.py`。
- 触发方式：客户端 `REACTIONS` 表（正则 → 台词键）决定「用户说什么时先回哪句」；`MURMURS` 决定空闲时说什么。
- 播放入口统一是 `SPEAKER.sayReaction(key, text, onStart)`，会排进同一条音频时间轴，不会和回复语音重叠。

## 一点十、双引擎（api_v2 / GSV-TTS-Lite）

包里带两套推理实现，**共用同一套权重与参考音**，音色一致，只是速度/显存不同。

| | api_v2（默认） | lite |
|---|---|---|
| 实现 | `tts/gs_api.py`（GPT-SoVITS 官方 api_v2，9880） | `tts/gsv_lite_server.py`（GSV-TTS-Lite，9882） |
| 依赖 | 系统 python + `tts/gptsovits` 引擎树 | 独立 venv `tts/gsvenv` + `pip install gsv-tts-lite` |
| 模型目录 | `tts/gptsovits/...`（自重） | `tts/gsv-models/`（首次运行自动下 1.28GB） |
| 流式首字节 | 0.61 s | 0.21–0.38 s |
| 整句耗时 | 2.3 s | 0.5–0.7 s |
| 显存峰值 | 2.7 GB | 1.2 GB |

安装 lite：

```powershell
python -m venv --system-site-packages tts\gsvenv
tts\gsvenv\Scripts\pip install gsv-tts-lite
# 首次调用会自动把模型下到 tts/gsv-models（走 ModelScope，无需 HF）
```

切换（改配置即可，宿主会按需拉起 9882）：

```powershell
curl -X POST http://127.0.0.1:<端口>/sandrone/config -H "content-type: application/json" -d "{\"voice\":{\"engine\":\"lite\"}}"
```

两个必须知道的坑（已在服务端修好，改代码时别删）：

1. `langid` 会把「语音回路已接通」判成吴语 `wuu`，而 LangSegment 只保留 `zh/en/ja/ko`，**整段文本会被静默丢弃**。`gsv_lite_server.py` 里把中文族标签统一折算成 `zh`，`api_v2` 那条链路仍需同样补丁（`gs_api.py` 里可加）。
2. CUDA Graph 捕获期间 cuDNN 的 SDPA 会崩（`operation not permitted when stream is capturing`），服务端固定 `EFFICIENT_ATTENTION`。

低配机器降级顺序：`lite` → 关 `use_flash_attn`（已默认关）→ `SANDRONE_LITE_GAIN` 只影响响度不影响负载 → 最后才是纯 CPU（RTF 约 1.5–2）。

## 一点十一、音色与风格的解耦

Lite 引擎把两件事拆开了：

| 参数 | 决定什么 | 取值 |
|---|---|---|
| `timbre` | 谁在说（声纹） | `sandrone`（默认）/ `alt-a` / `alt-b` |
| `pool` | 怎么念（韵律、语速） | `cool` / `warm` / `tease` / `tired` |
| `speed` | 语速倍率 | 0.6–1.65，缺省按池 |

调用示例：

```json
POST /infer  {"text": "雪，茶凉了。", "pool": "warm", "timbre": "sandrone", "speed": 0.92}
```

宿主侧对应配置：`voice.timbre`（音色）与 `voice.poolSpeed`（是否按池套语速）。

实测（同一句，四风格）：时长 1.67–2.40 s、f0 中位 249–265 Hz、f0 标准差 44.6–60.5；跨风格声纹 0.79–0.91，与「同一人不同录音」的 0.88 同量级 → 换风格不跑音色。

要加新音色：把一段 3–10 s 干净原声放进 `tts/ref/`，在 `tts/gsv_lite_server.py` 的 `TIMBRES` 里加一行即可，**不需要重新训练**。
