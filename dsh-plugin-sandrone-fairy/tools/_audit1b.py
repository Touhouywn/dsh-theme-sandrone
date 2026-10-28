import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = ROOT + r"\client.js"
s = io.open(p, encoding="utf-8").read().replace("\r\n", "\n")

# 1. streamOn 显式初值
if "streamOn: true" not in s:
    old = "      playingQueue: false,"
    assert s.count(old) == 1
    s = s.replace(old, "      playingQueue: false,\n      streamOn: true,          // false 时退回「整句合成再播」的老路")

# 2. 全局配置缓存
anchor = "let USER_NAME = '雪'"
assert s.count(anchor) == 1
s = s.replace(anchor, "let USER_NAME = '雪'\nlet PLUGIN_CFG = null")

uniq = "      const parts = (cfg && cfg.parts) || { splash: true, pet: true, voice: true }"
assert s.count(uniq) == 1
s = s.replace(uniq, uniq + "\n      PLUGIN_CFG = cfg")

# 3. 开屏时间轴按 skipMs 推导
old3 = "        const leave = window.setTimeout(() => setLeaving(true), 6400)"
assert s.count(old3) == 1
s = s.replace(old3, """        const skipMs = Math.max(4200, Math.min(20000, Number((PLUGIN_CFG && PLUGIN_CFG.splash && PLUGIN_CFG.splash.skipMs) || 7600)))
        const leaveAt = Math.max(2000, skipMs - 1200)
        const greetAt = Math.max(600, skipMs - 3700)
        const sayGreeting = !(PLUGIN_CFG && PLUGIN_CFG.splash && PLUGIN_CFG.splash.greeting === false)
        const leave = window.setTimeout(() => setLeaving(true), leaveAt)""")

old4 = "        const hi = window.setTimeout(() => { SPEAKER.sayClip('welcome', '……哼，回来了。我又没在等你。……茶还热着，坐下吧。') }, 3900)"
assert s.count(old4) == 1
s = s.replace(old4, """        const hi = sayGreeting
          ? window.setTimeout(() => { SPEAKER.sayClip('welcome', '……哼，回来了。我又没在等你。……茶还热着，坐下吧。') }, greetAt)
          : null""")

assert s.count("        }, 7600)") == 1
s = s.replace("        }, 7600)", "        }, skipMs)")
s = s.replace("window.clearTimeout(hi)", "if (hi) window.clearTimeout(hi)")

# 4. 尺寸吃配置
old5 = "        const w = Math.min(400, window.innerWidth * 0.29)"
if s.count(old5) == 1:
    s = s.replace(old5, "        const cap = Math.max(160, Math.min(560, Number((PLUGIN_CFG && PLUGIN_CFG.pet && PLUGIN_CFG.pet.size) || 400)))\n        const w = Math.min(cap, window.innerWidth * 0.29)")
else:
    print("!! fairySize anchor missing:", s.count(old5))

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("client patched")
