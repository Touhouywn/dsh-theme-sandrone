"""按雪的听感逐条重烘（第二轮精修）。

每条给出：新台词（如果有改写）/ 参考音池 / 语速。改完同步 tts/pack.json、
tts/pack_gs.py（POOL_OF + SPEED_OVERRIDE）、client.js（GREET_TEXT 与 REACTIONS 文案），
旧文件备份到 preview/fix2/old/。
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(BASE, "tts", "pack.json")
PKGS = os.path.join(BASE, "tts", "pack_gs.py")
CLIENT = os.path.join(BASE, "client.js")
OLD = os.path.join(BASE, "preview", "fix2", "old")

# key: (新文本 or None, 池, 语速, 说明)
FIX = {
    "welcome-back": ("回来了。……茶凉了，我去换一杯。", "tease", 0.98, "换池贴近 01；避开「重泡」的读音"),
    "greet-morning": ("醒了？……我又不是特意来催你的呢。……早啊。", "tease", 0.95, "「早啊」拉长 + 加「呢」"),
    "greet-afternoon": ("下午了。有要一起想的，就说。……今天，心情还不坏。", "warm", 0.95, "换短句，避开绕口的连续字"),
    "whisper-water": ("水凉了，换一杯。", "tired", 0.90, "缩短 + 放慢"),
    "react-hello": ("来了。坐。茶还热着。", "cool", 0.90, "改短句、压平语调"),
    "react-thanks": (None, "tease", 0.88, "只放慢，求清晰"),
    "react-tired": ("累了就靠一会儿。剩下的我来。", "tired", 0.90, "去掉「推演我来跑」这个绕口短语"),
    "react-night": (None, "tired", 0.88, "更轻更慢"),
    "react-morning": ("早。……我顺手泡的。不是特意等你。", "warm", 0.95, "B 版音色，整体降 1 半音"),
    "react-wake": ("……几点。再躺三十秒，别叫我。", "tired", 0.88, "「几点」后补厌倦感"),
    "react-goodnight": (None, "tired", 0.88, "放慢"),
    "idle-noon": ("午饭时间。别拿一杯水就把自己打发了。", "cool", 0.92, "改写，语序更顺"),
    "farewell": ("去吧。我在这。……回头见。", "warm", 0.95, "补一句，别太短"),
}


def load(path):
    return io.open(path, encoding="utf-8").read().replace("\r\n", "\n")


def save(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def main():
    apply = "--apply" in sys.argv
    os.makedirs(OLD, exist_ok=True)

    pack = json.loads(load(PACK))
    pkg = load(PKGS)
    client = load(CLIENT)

    changed = []
    for key, (text, pool, speed, why) in FIX.items():
        if text and pack.get(key) != text:
            pack[key] = text
            changed.append(key)

        # POOL_OF
        pat = re.compile(r'("%s": )"(\w+)"' % re.escape(key))
        if pat.search(pkg):
            pkg = pat.sub(lambda m: m.group(1) + '"%s"' % pool, pkg, count=1)

        # SPEED_OVERRIDE：存在则改值，不存在则插入
        sp = re.compile(r'("%s": )[0-9.]+' % re.escape(key))
        if sp.search(pkg):
            pkg = sp.sub(lambda m: m.group(1) + str(speed), pkg, count=1)
        else:
            pkg = pkg.replace(
                "SPEED_OVERRIDE = {\n",
                'SPEED_OVERRIDE = {\n    "%s": %s,\n' % (key, speed),
                1,
            )

        if not text:
            continue
        # client.js：GREET_TEXT 与 REACTIONS 文案同步
        client = re.sub(
            r"(clip: '%s', text: ')[^']*(')" % re.escape(key),
            lambda m: m.group(1) + text + m.group(2),
            client,
        )
        client = re.sub(
            r"(%s: ')[^']*(')" % re.escape(key),
            lambda m: m.group(1) + text + m.group(2),
            client,
        )

    if apply:
        save(PACK, json.dumps(pack, ensure_ascii=False, indent=2) + "\n")
        save(PKGS, pkg)
        save(CLIENT, client)
        print("[apply] 已写入 pack.json / pack_gs.py / client.js")
        for key in FIX:
            src = os.path.join(BASE, "assets", "voice", key + ".m4a")
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(OLD, key + ".m4a"))
        print("[apply] 旧音频已备份到 preview/fix2/old/")

    for key, (text, pool, speed, why) in FIX.items():
        cur = pack.get(key, "")
        print("%-17s %-6s %.2f  %s%s" % (key, pool, speed, why, "" if text is None or text == cur else "  [文本已改]"))


if __name__ == "__main__":
    main()
