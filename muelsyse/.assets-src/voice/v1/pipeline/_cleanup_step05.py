"""一次性清理：删掉 step05 里被 21 键版本取代的旧模板逻辑。

- 删 semantic_ok（改用 intents.template_semantic_ok）
- 删 OVERRIDES + 旧 build_templates（11 键那版）
"""

from pathlib import Path

p = Path(r"E:\AI-theme\columbina\.assets-src\voice\v2\pipeline\step05_build.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

# 块 A：semantic_ok
start = next(i for i, l in enumerate(lines) if l.startswith("def semantic_ok("))
end = next(i for i, l in enumerate(lines) if l.startswith("def pick(entries"))
del lines[start:end]

# 块 B：OVERRIDES + 旧 build_templates
start = next(i for i, l in enumerate(lines) if l.startswith("# 规则选出来的段里"))
end = next(i for i, l in enumerate(lines) if l.strip() == "return templates, unmapped")
del lines[start:end + 1]

text = "".join(lines)
# 收一下连续空行
while "\n\n\n\n" in text:
    text = text.replace("\n\n\n\n", "\n\n\n")
p.write_text(text, encoding="utf-8")
print("lines now", len(text.splitlines()))
print("semantic_ok left:", "def semantic_ok" in text)
print("OVERRIDES left:", "OVERRIDES" in text)
print("build_templates count:", text.count("def build_templates"))
