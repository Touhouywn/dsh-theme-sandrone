# 缪尔赛思实时语音 · Pro 准备件（live-prep）

> 状态：Pro 侧初版，供执行稿引用。所有「提案」项仍需用户/听感确认（P1/P2）。
> 用途：L2 翻译环术语表、L3 TTS 参考档、L5 思考音清单、L1 catalog 映射。

## 1. zh→ja 术语表（Pro 初版，冻结后翻译环只做机械替换）

| 中文 | 日文 | 备注 |
| --- | --- | --- |
| 博士 | ドクター | 称呼，全句最高频 |
| 罗德岛 | ロドス | 专名 |
| 莱茵生命 | ライン生命 | 专名 |
| 莱茵 | ライン | 简写 |
| 缪尔赛思 | ミュルジス | 自称 |
| 生态科 | 生態課 | 职位 |
| 生态学 | 生態学 | |
| 精灵 | エルフ | |
| 巨兽 | 巨獣 | 原文用词 |
| 结晶 | 結晶 | |
| 琥珀 | 琥珀 | |
| 萨米 | サーミ | 地区 |
| 麦哲伦 | マゼラン | 人名 |
| 克丽斯腾 | クリステン | 人名 |
| 明日方舟 | アークナイツ | |

术语表只钉高频专名；其余交给翻译模型，翻译环不因术语表外词停摆。

## 2. TTS 参考音频候选（授权已获 2026-10-27：官方切片可做参考；听感定档仍 P2）

| 提案 | 候选 | 理由 |
| --- | --- | --- |
| 主参考 | CN_034 戳一下（7.54s 整条） | 长度正好、完整句、vocal 轨无 BGM |
| 备参考 | CN_011 干员报到 前 10s（词帽剪） | 自我介绍腔，音色典型；prompt 文本 = 官方 ja_text |
| 备参考 | CN_005 晋升后交谈1 中段 8–10s | 情感起伏自然 |

- prompt 文本一律用官方 ja_text（skeleton 里已有，无需转写）。
- GPT-SoVITS api_v2 与 CosyVoice2 worker 都支持 ja；最终引擎与档位在 L3 延迟表后定。

## 3. 思考音候选（已确认要切 2026-10-27；从 vocal 母带词帽新切，P2 听感终审）

| 相 | 提案 | 来源 |
| --- | --- | --- |
| 起相 hum | 「ふぅ～」~1.2s | CN_005 头部（源时间 97.06s 起，按 words.json 词帽切） |
| 中相（限 2 声） | 「ふぅ、少なくとも…」前 ~2.0s | CN_034 头部 |
| 收相 ack | CN_021 なぁに？（0.76s 整条） | 已入库，无需新切 |
| 备选 | CN_024 この水滴はどこに落ちるのかしら。（2.98s） | 已入库 |

初版清单空 = 静默；听感确认后再填 thinking.json。

## 4. catalog 映射（L1 执行稿用；从已发布产物生成，不重切）

- aligned.tsv 的 37 条 ok 行 → `catalog.json`（schema 对齐 columbina-voice v2）：
  `id=CN_xxx`、`file=clips/CN_xxx.wav`、`text=ja_text`（检索面）、`asrText=whisper_ja`、
  `duration=dur_s`、`sourceStart/sourceEnd=源时间`、`tags=[trigger]`、`stem=vocals`。
- `templates.json`：trigger（HOME_SHOW 等）→ clip id 列表。

## 5. 环境事实（执行稿写死，勿改）

| 项 | 值 |
| --- | --- |
| GPT-SoVITS | `E:\AI-theme\columbina\.runtime\GPT-SoVITS`（run_api.py / api_v2.py；权重 gsv-v2final-pretrained + sv/eres2netv2 齐全）；启动 `columbina\.assets-src\voice\start-sovits.ps1`，port 9880；RTX 4060，冷启动 ~20s，一句 ~1s |
| CosyVoice2 worker | `dsh-plugin-sandrone-fairy\tts\worker.py`（`python worker.py <ref.wav> <cache_dir>`，JSON 行协议，24k wav；复用 clone.py 的 torch/load_wav 补丁） |
| 现状 | 9880 未运行，两引擎均未常驻；L3 阶段需拉起 |
| 检索阈值 | short 0.45 / long 0.42 / maxClips 2（ja 归一，沿用） |

## 6. 参照实现的架构事实（columbina-voice 实测，执行稿直接引用）

- 宿主路由（ROUTE=/columbina-voice）：GET /status、GET /catalog、POST /select、
  GET /clip/<id>、GET /thinking、POST /speak、GET /synth?text=..&stream=1。
- 混合规划器在 index.js L254：L4 技术句过滤 → 短句切片 → 长句合成；降级梯合成→切片→静默。
- 客户端（client.js）：SELECT_URL/THINK_URL；思考选择器三候选
  `[class*="thinking" i]`、`[class*="reasoning" i]`、`[class*="thought" i]`；
  事件命名空间 `columbina:voice:`；正文稳定 ~1200ms 后触发 select。
- 合成适配器（synth.js）：全部由 `COLUMBINA_TTS_*` 环境变量驱动；
  无 `COLUMBINA_TTS_REF` 时引擎停用、只走切片；api_v2 协议
  `media_type=raw + streaming_mode=3` 流式，wav + 缓存整句；
  拉起器 30s 窗口单次 spawn；TTFB 预算 5000ms。
- 设计红线（沿用）：参考音频必须属于本角色，绝不回退到其他角色的声音。
- Muelsyse 版对应命名：ROUTE=/muelsyse-voice，环境变量 `MUELSYSE_TTS_*`，
  事件命名空间 `muelsyse:voice:`，catalog 的 text 字段 = ja_text。
