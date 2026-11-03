"""单独生成一页「价值与意义」，用于插入答辩 PPT 第四部分。

为什么要新开一个文件：主 PPT 频繁被 PowerPoint 占用导致写入失败，
单独出一页既不会卡住主构建，也方便直接拖进现有演示文稿。

样式与主 PPT 完全一致：同一套配色（暖灰底 #FAF8F4、强调砖红 #E4572E）、
同一字体（微软雅黑）、同一套 kicker + headline 版式。
"""

import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BG = RGBColor(0xFA, 0xF8, 0xF4)
INK = RGBColor(0x23, 0x20, 0x1C)
INK2 = RGBColor(0x5C, 0x56, 0x4C)
MUTED = RGBColor(0x94, 0x8C, 0x7E)
ACCENT = RGBColor(0xE4, 0x57, 0x2E)
SUBTLE = RGBColor(0xF4, 0xF1, 0xEA)
BORDER = RGBColor(0xE7, 0xE1, 0xD5)
FONT = "微软雅黑"

W, H = 13.333, 7.5
OUT = "paper/世界语言赛博活力图谱_价值与意义.pptx"


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
        r.font.size = __import__("pptx.util", fromlist=["Pt"]).Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = name
    return box


def rect(s, l, t, w, h, fill, border=None, radius=None):
    from pptx.enum.shapes import MSO_SHAPE
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(l), Inches(t), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if border is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = border
        shp.line.width = __import__("pptx.util", fromlist=["Pt"]).Pt(0.75)
    shp.shadow.inherit = False
    if radius:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    return shp


def kicker(s, text, l=0.72, t=0.52):
    tb(s, l, t, 8.0, 0.34, text, 11, ACCENT, True)


def headline(s, text, t=0.92, size=31, w=11.9):
    tb(s, 0.72, t, w, 0.9, text, size, INK, True, spacing=1.15)


prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)
s = prs.slides.add_slide(prs.slide_layouts[6])
s.background.fill.solid()
s.background.fill.fore_color.rgb = BG

kicker(s, "价值 · 这项工作真正留下了什么")
headline(s, "把散在五个体系里的语言数据，接成一张能查的表", t=0.92, size=29)

# ---- 左栏：三点价值，写成连贯段落
paras = [
    ("数据是半自采的",
     "五个来源里，WALS 与 Glottolog 的结构描写、Wikidata 的编号映射来自公开数据集，"
     "而维基各版本的规模、月度浏览量、以及每门语言的文献清单，是我按接口逐条抓取并汇总的。"
     "也就是说，这份数据不是把现成表格拼起来，其中相当一部分需要自己采集。"),
    ("真正的工作量在聚合",
     "同一门语言的信息原本分散在四套互不相干的体系里：结构描写在 WALS，"
     "濒危评定在 UNESCO 与 Glottolog，文献目录在 Glottolog 的参考文献库，"
     "网络关注度在维基媒体的接口。它们各自使用自己的编号，无法直接连接，"
     "任何跨体系的比较都必须先解决对齐问题。"),
    ("一套三向编码对齐",
     "我以 Glottolog 为枢纽，建立了 WALS 码、Glottocode 与 ISO 639-3 之间的三向映射，"
     "并逐个处理了「一个语种被多个维基版本认领」「三套体系撞码」这些边界情况。"
     "对齐之后，按语法特征、语系、濒危等级与增长率任意组合筛选，只剩一次点击的距离。"),
]
y = 1.74
for h, d in paras:
    tb(s, 0.72, y, 3.0, 0.4, h, 12.5, ACCENT, True)
    tb(s, 0.72, y + 0.36, 7.35, 1.28, d, 10.5, INK2, spacing=1.58)
    y += 1.50

# ---- 右栏：对齐示意 + 数字条
rect(s, 8.55, 1.74, 4.1, 3.05, SUBTLE, radius=0.06)
tb(s, 8.85, 1.90, 3.5, 0.36, "三向编码对齐", 12, INK, True)
rows = [
    ("WALS 码", "deu"),
    ("Glottocode", "deur1238"),
    ("ISO 639-3", "der"),
]
for i, (k, v) in enumerate(rows):
    yy = 2.48 + i * 0.62
    tb(s, 8.85, yy, 1.55, 0.34, k, 9.5, MUTED)
    tb(s, 10.5, yy - 0.02, 2.0, 0.36, v, 11.5, INK, True, name="Consolas")
    if i < 2:
        rect(s, 8.85, yy + 0.44, 3.5, 0.008, BORDER)
tb(s, 8.85, 4.42, 3.55, 0.42,
   "同一门语言，三套编号 —— 这是所有跨体系比较的前提", 9, MUTED, spacing=1.45)

# ---- 底部数字条
stats = [("157,736", "行数据"), ("9", "张表"), ("2,662", "门语言"),
         ("5", "个公开来源"), ("3", "套编码对齐")]
for i, (n, lab) in enumerate(stats):
    x = 0.72 + i * 2.42
    tb(s, x, 6.56, 1.7, 0.5, n, 21, ACCENT, True, name="Consolas")
    tb(s, x, 7.04, 1.9, 0.32, lab, 9.5, MUTED)

prs.save(OUT)
print(f"  已生成 {OUT}（{len(prs.slides)} 页）")
