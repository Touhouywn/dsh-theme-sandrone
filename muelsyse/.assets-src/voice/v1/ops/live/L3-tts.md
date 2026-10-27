# L3 TTS 引擎接入 + 参考档

## 目标
`GET /muelsyse-voice/synth?text=<ja>&stream=1` 出日文语音：GPT-SoVITS 主引擎、CosyVoice2 worker 兜底；参考音频用官方切片（用户已授权）。

## 步骤
1. 写 `synth.js`：复制 columbina 版改三处——
   - 环境变量全改 `MUELSYSE_TTS_*`（API/REF/REF_TEXT/LAUNCHER/PYTHON/SPEED/TTFB_MS/TIMEOUT_MS/WAKE_MS/CACHE）；
   - 拉起器是 ps1：`spawn('pwsh', ['-File', <launcher>])`（columbina 是 python 脚本，这里必须换成 pwsh）；
   - 红线断言：REF 必须指向本插件 `assets\clips\` 内文件，否则 ttsConfigured()=false（不跨角色回退）。
2. 参考档：主参考 `assets\clips\CN_034.wav`（整条 7.54s），REF_TEXT = 官方 ja_text
   （从 catalog.json 该条 text 取，即「ふぅ、少なくとも…」）；备参考 CN_011 前 10s（ffmpeg
   `-t 10` 剪到 `assets\refs\CN_011-head10.wav`，REF_TEXT 用官方文本前两句）——先用主参考跑延迟表，
   音色不稳再换（Pro 定）。
3. 拉起：`MUELSYSE_TTS_LAUNCHER=E:\AI-theme\columbina\.assets-src\voice\start-sovits.ps1`；
   WAKE_MS 35000（GS 冷启动 ~20s）。
4. 兜底：GS 不可用 → CosyVoice2 worker（`dsh-plugin-sandrone-fairy\tts\worker.py`，
   `python worker.py <ref.wav> <cache_dir>`，JSON 行协议，24k wav；ref 仍用 CN_034）。
5. `/synth` 无 stream → 整句 wav + 缓存；有 stream → api_v2 `media_type=raw + streaming_mode=3` PCM 透传。
6. 引擎未配置/不可用时 `/synth` 回 503，body 带 `fallback` 字段（给该句切片兜底）。

## 断言
- 引擎开着：`/synth?text=こんにちは&stream=1` 出 PCM 流；TTFB ≤5s。
- 引擎关着：/synth 503 + fallback；/status 里 ttsConfigured 反映真实状态。

## 参数冻结（默认值同 columbina）
SPEED 0.9；TTFB_MS 5000；TIMEOUT_MS 120000；WAKE_MS 35000；CACHE `%TEMP%\muelsyse-voice-cache\`。

## 降级表
| 情况 | 动作 |
| --- | --- |
| GS 不可达/超时 | 降 CosyVoice2 worker |
| worker 也不可用 | 该句检索；低分 → 静默 + missing |
| 合成音频 RMS < −40dB 或削波 | 重试 1 次，仍异常降级 |
| TTFB >5s/句 | 该句降级；整轮 >20% → HOLD |
