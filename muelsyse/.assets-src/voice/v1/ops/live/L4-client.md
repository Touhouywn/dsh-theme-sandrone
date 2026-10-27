# L4 浏览器半边（watcher + 混合播放）

## 目标
GUI 里：正文稳定后走 /speak 计划播放（clip 用 HTMLAudio，tts 用 PCM 流），互斥、开关、事件照发。

## 步骤
1. 写 `client.js`：复制 columbina client.js，改——
   - URL 常量：`/muelsyse-voice/speak|select|thinking|synth`；
   - 事件命名空间 `muelsyse:voice:`；
   - 按钮/标记 id 换 `muelsyse-voice:*`。
2. 正文 watcher：稳定 ~1200ms → 取段落 → `POST /speak` → 按 segments 顺序播放：
   - clip 段：HTMLAudio 播 `/clip/<id>`；
   - tts 段：fetch `/synth?text=..&stream=1` → AudioContext 边收边播（参照 columbina speakStable）；
   - 503 → 播 fallback.clips；仍失败 → 静默 + missing。
3. playToken 互斥沿用：新正文先闭嘴；同会话单流。
4. 可选 ♪ 开关（默认开），关掉只影响发声，不影响事件。

## 断言
- 页面实测三例各一次（意图句=切片、技术句=静默、长正文=合成或降级），由用户 GUI 侧配合；
  flash 先跑 `tools\test_client.mjs` 模拟三例。

## 降级表
| 情况 | 动作 |
| --- | --- |
| AudioContext 不可用 | 整段落为 HTMLAudio 播缓存 wav（/synth 不带 stream） |
| 事件 API 不可用 | 静默跳过，发声不受影响 |
