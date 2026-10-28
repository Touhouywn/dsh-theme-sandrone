import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = ROOT + r"\client.js"
s = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")

# ── 1. streamOn 显式初值（之前只被读、从没被赋值，等于恒真）
old = "      playingQueue: false,"
assert s.count(old) == 1
s = s.replace(old, "      playingQueue: false,\n      streamOn: true,          // false 时退回「整句合成再播」的老路")

# ── 2. 缓存配置，供开屏计时与尺寸使用
old2 = "        if (cfg.voice && cfg.voice.userName) USER_NAME = String(cfg.voice.userName)"
assert s.count(old2) == 1
s = s.replace(old2, old2 + """
        PLUGIN_CFG = cfg""")

anchor = "let USER_NAME = '雪'"
assert s.count(anchor) == 1
s = s.replace(anchor, "let USER_NAME = '雪'\nlet PLUGIN_CFG = null")

# ── 3. 开屏时间轴改成按 skipMs 推导；greeting=false 时不说话
old3 = """        const leave = window.setTimeout(() => setLeaving(true), 6400)"""
new3 = """        const skipMs = Math.max(4200, Math.min(20000, Number((PLUGIN_CFG && PLUGIN_CFG.splash && PLUGIN_CFG.splash.skipMs) || 7600)))
        const leaveAt = Math.max(2000, skipMs - 1200)
        const greetAt = Math.max(600, skipMs - 3700)
        const sayGreeting = !(PLUGIN_CFG && PLUGIN_CFG.splash && PLUGIN_CFG.splash.greeting === false)
        const leave = window.setTimeout(() => setLeaving(true), leaveAt)"""
assert s.count(old3) == 1
s = s.replace(old3, new3)

old4 = """        const hi = window.setTimeout(() => { SPEAKER.sayClip('welcome', '……哼，回来了。我又没在等你。……茶还热着，坐下吧。') }, 3900)"""
new4 = """        const hi = sayGreeting
          ? window.setTimeout(() => { SPEAKER.sayClip('welcome', '……哼，回来了。我又没在等你。……茶还热着，坐下吧。') }, greetAt)
          : null"""
assert s.count(old4) == 1
s = s.replace(old4, new4)

s = s.replace("""        const done = window.setTimeout(() => {
          setStage('ready')""", """        const done = window.setTimeout(() => {
          setStage('ready')""")
s = s.replace("""          } catch (error) { /* ignore */ }
        }, 7600)""", """          } catch (error) { /* ignore */ }
        }, skipMs)""")

# 清理定时器时允许 hi 为 null
s = s.replace("window.clearTimeout(hi)", "if (hi) window.clearTimeout(hi)")

# ── 4. 尺寸吃配置：fairySize 用 cfg.pet.size 作为上限
old5 = "        const w = Math.min(400, window.innerWidth * 0.29)"
if s.count(old5) == 1:
    s = s.replace(old5, "        const cap = Math.max(160, Math.min(560, Number((PLUGIN_CFG && PLUGIN_CFG.pet && PLUGIN_CFG.pet.size) || 400)))\n        const w = Math.min(cap, window.innerWidth * 0.29)")
else:
    print("!! fairySize anchor missing")

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("client config wiring done")
