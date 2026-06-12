"""Generate the Stream Deck plugin PNG icons.

Stream Deck does NOT render SVG icons (they show as blank), so the plugin ships PNGs.
This regenerates them: solid rounded tiles – dark = idle, red = active, green = start –
plus a small "VS" action/plugin icon. Run after changing colours/sizes:

    python3 tools/gen_streamdeck_icons.py

Needs Pillow (`pip install pillow`). Writes base + @2x into the plugin's icons/ folder.
"""

import os
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(REPO, "streamdeck", "cz.vysledkovyservis.sdPlugin", "icons")
FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"


def tile(size, fill, border):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = max(2, round(size * 0.125))
    bw = max(1, round(size * 0.02))
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius,
                        fill=fill, outline=border, width=bw)
    return img


def lettered(size, fill, text="VS"):
    img = tile(size, fill, fill)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, round(size * 0.5))
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text(((size - (r - l)) / 2 - l, (size - (b - t)) / 2 - t), text,
           font=font, fill="#ffffff")
    return img


def save(img_fn, name, base):
    img_fn(base).save(os.path.join(ICONS, name + ".png"))
    img_fn(base * 2).save(os.path.join(ICONS, name + "@2x.png"))


if __name__ == "__main__":
    # Key tiles (72 / 144) – fill + border colours
    save(lambda s: tile(s, "#2b2b2e", "#444444"), "key", 72)         # idle
    save(lambda s: tile(s, "#F52525", "#ff7a7a"), "key-active", 72)  # active view / broadcasting
    save(lambda s: tile(s, "#2e9e4f", "#7ad99a"), "key-start", 72)   # start broadcast
    # Action list icon (20 / 40) and plugin/category icon (28 / 56)
    save(lambda s: lettered(s, "#F52525"), "action", 20)
    save(lambda s: lettered(s, "#F52525"), "plugin", 28)
    print("Generated:", sorted(f for f in os.listdir(ICONS) if f.endswith(".png")))
