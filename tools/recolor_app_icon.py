"""Recolor the app icon (icon.icns) by rotating its hue, keeping the white flame.

The icon is a flame on a coloured gradient. Hue rotation keeps the flame (white,
no saturation) and the gradient, and only shifts the coloured background. Current
base is turquoise (~175° from the original red).

    python3 tools/recolor_app_icon.py <degrees>

e.g. `45` shifts turquoise toward blue. Needs Pillow + macOS sips/iconutil.
Overwrites icon.icns – commit the result and rebuild the .app to ship it.
"""

import os
import subprocess
import sys
import tempfile

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICNS = os.path.join(REPO, "icon.icns")


def recolor(img, deg):
    r, g, b, a = img.split()
    hsv = Image.merge("RGB", (r, g, b)).convert("HSV")
    h, s, v = hsv.split()
    off = int(deg / 360 * 255) % 256
    h = h.point(lambda x: (x + off) % 256)  # white/gray (S=0) stays unchanged
    rr, gg, bb = Image.merge("HSV", (h, s, v)).convert("RGB").split()
    return Image.merge("RGBA", (rr, gg, bb, a))


def main(deg):
    with tempfile.TemporaryDirectory() as tmp:
        src_png = os.path.join(tmp, "src.png")
        subprocess.run(["sips", "-s", "format", "png", ICNS, "--out", src_png],
                       check=True, capture_output=True)
        icon = recolor(Image.open(src_png).convert("RGBA"), deg)

        iconset = os.path.join(tmp, "icon.iconset")
        os.makedirs(iconset)
        for sz in (16, 32, 128, 256, 512):
            icon.resize((sz, sz), Image.LANCZOS).save(
                os.path.join(iconset, "icon_%dx%d.png" % (sz, sz)))
            icon.resize((sz * 2, sz * 2), Image.LANCZOS).save(
                os.path.join(iconset, "icon_%dx%d@2x.png" % (sz, sz)))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", ICNS], check=True)
    print("icon.icns přebarven o %s° – commitni a zbuilduj .app (icon není v in-app updatu)." % deg)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Použití: python3 tools/recolor_app_icon.py <stupně>")
    main(float(sys.argv[1]))
