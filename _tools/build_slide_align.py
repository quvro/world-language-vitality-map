"""生成一页「跨源编码对齐」，文字按用户给定内容。

版式：
  上排  维基百科（ISO 639-1）  ←→  三级匹配规则  ←→  WALS（ISO 639-3）
  中排  宏观语言说明（zho / cmn / yue / nan）
  下排  其二 域名 ≠ 代码    ｜    其三 一个条目被多个版本认领
"""

import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BG = RGBColor(0xFA, 0xF8, 0xF4)
INK = RGBColor(0x23, 0x20, 0x1C)
INK2 = RGBColor(0x5C, 0x56, 0x4C)
MUTED = RGBColor(0x94, 0x8C, 0x7E)
ACCENT = RGBColor(0xE4, 0x57, 0x2E)
SUBTLE = RGBColor(0xF4, 0xF1, 0xEA)
BORDER = RGBColor(0xE7, 0xE1, 0xD5)
BLUE = RGBColor(0x4A, 0x6E, 0x8A)
FONT = "微软雅黑"
MONO = "Consolas"


def tb(s, l, t, w, h, text="", size=18, color=INK, bold=False,
       align=PP_ALIGN.LEFT, spacing=1.25, name=FONT):
    box = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = name


def rect(s, l, t, w, h, fill, border=None, radius=None, shape=None):
    shp = s.shapes.add_shape(
        shape or (MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE),
        Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if border is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = border
        shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    if radius:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    return shp


def arrow(s, l, t, w, h=0.13):
    rect(s, l, t, w, h, MUTED, shape=MSO_SHAPE.RIGHT_ARROW)


prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
s = prs.slides.add_slide(prs.slide_layouts[6])
s.background.fill.solid()
s.background.fill.fore_color.rgb = BG

tb(s, 0.72, 0.48, 9.0, 0.32, "数据采集 · 最难的一步是对齐", 11, ACCENT, True)
tb(s, 0.72, 0.84, 11.9, 0.62,
   "同一门语言，两套编码：一个是两字母，一个是三字母", 27, INK, True, spacing=1.1)
tb(s, 0.72, 1.46, 11.9, 0.34,
   "维基百科用 ISO 639-1，只覆盖约一百八十种主要语言；WALS 用 ISO 639-3，三个字母覆盖七千多种",
   11, MUTED)

# ---------------- 上排：左 / 中 / 右
# 左：维基百科
rect(s, 0.72, 1.94, 3.5, 2.28, SUBTLE, radius=0.05)
tb(s, 1.00, 2.08, 3.0, 0.34, "维基百科", 13, INK, True)
tb(s, 1.00, 2.44, 3.0, 0.72,
   "页面浏览量\n站点规模与项目数", 10, INK2, spacing=1.5)
tb(s, 1.00, 3.16, 2.2, 0.3, "使用编码", 8.5, MUTED)
tb(s, 1.00, 3.42, 2.6, 0.4, "ISO 639-1  ·  两字母", 11.5, ACCENT, True)
tb(s, 1.00, 3.78, 3.0, 0.3, "例：zh  覆盖约 180 种", 9.5, INK2, name=MONO)

# 中：三级匹配
rect(s, 4.46, 1.94, 4.42, 2.28, None, BORDER, radius=0.05)
tb(s, 4.72, 2.06, 4.0, 0.32, "匹配规则（依次尝试）", 11, INK, True)
rules = [
    ("①", "按代码直接匹配"),
    ("②", "两字母码转三字母再试"),
    ("③", "到 Wikidata 查该变体隶属哪个宏观语言"),
]
for i, (n, t) in enumerate(rules):
    yy = 2.44 + i * 0.5
    tb(s, 4.72, yy, 0.32, 0.3, n, 10.5, ACCENT, True)
    tb(s, 5.12, yy - 0.01, 3.6, 0.42, t, 10.5, INK2, spacing=1.35)
tb(s, 4.72, 3.86, 3.9, 0.3, "转换后才可与 WALS 关联", 8.5, MUTED)

# 右：WALS
rect(s, 9.12, 1.94, 3.5, 2.28, SUBTLE, radius=0.05)
tb(s, 9.40, 2.08, 3.0, 0.34, "WALS", 13, INK, True)
tb(s, 9.40, 2.44, 3.0, 0.72,
   "192 个语法特征\n2,662 个变体", 10, INK2, spacing=1.5)
tb(s, 9.40, 3.16, 2.2, 0.3, "使用编码", 8.5, MUTED)
tb(s, 9.40, 3.42, 2.7, 0.4, "ISO 639-3  ·  三字母", 11.5, BLUE, True)
tb(s, 9.40, 3.78, 3.0, 0.3, "例：zho  覆盖七千多种", 9.5, INK2, name=MONO)

arrow(s, 4.24, 2.95, 0.2)
arrow(s, 8.90, 2.95, 0.2)

# ---------------- 宏观语言说明
rect(s, 0.72, 4.34, 11.9, 0.5, None, BORDER, radius=0.04)
tb(s, 0.96, 4.42, 11.5, 0.36,
   "宏观语言：ISO 639-3 把普通话、粤语、闽南语各自单列（cmn / yue / nan），"
   "又把中文整体登记成一个宏观语言（zho）；而 WALS 按变体收录 —— 所以 zho 这类码在 WALS 里无法直接查询。",
   9.5, INK2, spacing=1.4)

# ---------------- 下排两个坑
rect(s, 0.72, 5.02, 5.85, 2.12, SUBTLE, radius=0.05)
tb(s, 1.00, 5.14, 5.2, 0.32, "其二 · 域名不等于语言代码", 11.5, ACCENT, True)
tb(s, 1.00, 5.50, 5.25, 1.5,
   "粤语在 zh-yue、闽南语在 zh-min-nan、文言在 zh-classical。"
   "直接用语言代码拼域名，未必能取到有效数据。\n"
   "解法：改为从维基的站点列表接口读取真实域名。",
   9.5, INK2, spacing=1.5)

rect(s, 6.9, 5.02, 5.72, 2.12, SUBTLE, radius=0.05)
tb(s, 7.18, 5.14, 5.2, 0.32, "其三 · 一个条目被多个版本同时认领", 11.5, ACCENT, True)
tb(s, 7.18, 5.50, 5.15, 0.72,
   "WALS 有时把两种语言合并在同一条目：aze 同时被 az 与 azb 认领，"
   "ind 同时被 id 与 ms 认领 —— 流量会被混算。", 9.5, INK2, spacing=1.45)
tb(s, 7.18, 6.20, 5.15, 0.3, "解法：每条目只留一个版本，优先级依次为", 9, MUTED)
tb(s, 7.18, 6.48, 5.2, 0.55,
   "与 WALS 标注的 ISO 码一致 → 是两字母 639-1 码 → 关联步骤最少 → 总浏览量最高",
   9.5, INK, True, spacing=1.4)

OUT = "paper/世界语言赛博活力图谱_跨源编码对齐.pptx"
prs.save(OUT)
print(f"  已生成 {OUT}（{len(prs.slides)} 页）")
