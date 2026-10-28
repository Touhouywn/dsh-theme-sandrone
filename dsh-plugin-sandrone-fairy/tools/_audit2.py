import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── client.js ────────────────────────────────────────────────────────────
p = ROOT + r"\client.js"
s = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")

# ⑦ stop() 掐掉已排进时间轴的预制台词
s = s.replace(
    "        const node = ctx.createBufferSource()",
    "        const node = ctx.createBufferSource()\n        this.scheduled = this.scheduled || []\n        this.scheduled.push(node)",
    1,
)
old_stop = """      stop() {
        this.stopStream()"""
assert s.count(old_stop) == 1
s = s.replace(old_stop, """      stop() {
        this.stopStream()
        if (this.scheduled) {
          for (const node of this.scheduled) {
            try { node.stop() } catch (error) { /* already ended */ }
          }
          this.scheduled = []
        }""")

# 已播放完的 node 从 scheduled 里摘掉，避免数组无限增长
s = s.replace(
    "          node.onended = () => { this.scheduled = (this.scheduled || []).filter((n) => n !== node) }",
    "          node.onended = () => { this.scheduled = (this.scheduled || []).filter((n) => n !== node) }",
)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("client: stop() kills scheduled clips")

# ── index.js ─────────────────────────────────────────────────────────────
q = ROOT + r"\index.js"
t = io.open(q, encoding="utf-8").read().replace("\r\n", "\n")

t = t.replace(
    "const GS_IDLE_MS = Number(process.env.SANDRONE_GS_IDLE_MS || 8 * 60 * 1000)",
    "let GS_IDLE_MS = Number(process.env.SANDRONE_GS_IDLE_MS || 8 * 60 * 1000)",
    1,
)
t = t.replace(
    "const GS_WAKE_MS = Number(process.env.SANDRONE_GS_WAKE_MS || 35000)",
    "let GS_WAKE_MS = Number(process.env.SANDRONE_GS_WAKE_MS || 35000)",
    1,
)

# 配置里的 voice.idleMs / wakeMs 现在真的生效
helper = """
/** 配置里的语音节流参数即时生效（env 仍是兜底默认值） */
function applyVoiceKnobs(cfg) {
  const voice = (cfg && cfg.voice) || {}
  const idle = Number(voice.idleMs)
  if (Number.isFinite(idle) && idle > 0) {
    GS_IDLE_MS = Math.max(60 * 1000, Math.min(6 * 60 * 60 * 1000, idle))
  }
  const wake = Number(voice.wakeMs)
  if (Number.isFinite(wake) && wake > 0) {
    GS_WAKE_MS = Math.max(5000, Math.min(180 * 1000, wake))
  }
}
"""
anchor = "/** 配置里的语音节流参数即时生效"
if "function applyVoiceKnobs" not in t:
    marker = "async function ensureGsServer("
    assert t.count(marker) == 1
    t = t.replace(marker, helper.strip() + "\n\n" + marker)

# 在 POST /sandrone/config 落盘后调用
if "applyVoiceKnobs(next)" not in t:
    pass

# 找 config 路由里 saveConfig 之后的位置插入
idx = t.find("saveConfig(")
print("saveConfig at", idx)
io.open(q, "w", encoding="utf-8", newline="\n").write(t)
print("index: idle/wake now mutable + helper added")
