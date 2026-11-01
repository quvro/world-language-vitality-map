"""把两张示意图裁到内容边界（背景是纯色，留白很多），供论文插入。"""
import sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for name in ("01-mindmap", "02-pipeline"):
    p = f"paper/figs/{name}.png"
    im = Image.open(p).convert("RGB")
    bg = im.getpixel((2, 2))
    w, h = im.size
    px = im.load()
    # 逐像素找与背景差异明显的区域
    left, top, right, bottom = w, h, 0, 0
    step = 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 12:
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y
    m = 30
    box = (max(left - m, 0), max(top - m, 0), min(right + m, w), min(bottom + m, h))
    im.crop(box).save(p)
    print(f"  {name}: {w}x{h} -> {box[2]-box[0]}x{box[3]-box[1]}")
