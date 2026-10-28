"""Export the three extra pet models from the images the user sent."""

import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
PAD = 12
MAX_SIDE = 1200

SRC = {
    "figure-sit.png": os.path.join(ROOT, "assets", "figure-sit.png"),
    "figure-cake.png": os.path.join(ROOT, "assets", "figure-cake.png"),
    "figure-pout.png": os.path.join(ROOT, "assets", "figure-pout.png"),
}

for name, path in SRC.items():
    image = Image.open(path).convert("RGBA")
    box = image.getbbox()
    cropped = image.crop(box)
    wide = cropped.size[0] + PAD * 2
    tall = cropped.size[1] + PAD * 2
    scale = min(1.0, MAX_SIDE / float(max(wide, tall)))
    canvas = Image.new("RGBA", (int(wide * scale), int(tall * scale)), (0, 0, 0, 0))
    art = cropped.resize((int(cropped.size[0] * scale), int(cropped.size[1] * scale)), Image.LANCZOS)
    canvas.paste(art, (int(PAD * scale), int(PAD * scale)), art)
    target = os.path.join(OUT, name)
    canvas.save(target, optimize=True)
    print(name, canvas.size, round(os.path.getsize(target) / 1024), "KB")
