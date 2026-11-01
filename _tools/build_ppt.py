"""生成 10 分钟答辩 PPT（16:9，浅色暖调，与应用同一套视觉语言）+ 讲稿备注。"""
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BG = RGBColor(0xFA, 0xF8, 0xF4)
INK = RGBColor(0x23, 0x20, 0x1C)
INK2 = RGBColor(0x5C, 0x56, 0x4C)
MUTED = RGBColor(0x94, 0x8C, 0x7E)
ACCENT = RGBColor(0xE4, 0x57, 0x2E)
BORDER = RGBColor(0xE7, 0xE1, 0xD5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SUBTLE = RGBColor(0xF4, 0xF1, 0xEA)

FONT = "微软雅黑"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
W = 13.333
H = 7.5

FIG = "paper/figs"
NOTES: list[str] = []


def _font(run, name=FONT):
    run.font.name = name
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", name)


def slide(no: int | None = None, footer: str = ""):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    if no is not None:
        t = tb(s, 0.72, 6.93, 8.0, 0.32, footer, 10, MUTED)
        t.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
        n = tb(s, W - 1.4, 6.93, 0.8, 0.32, f"{no:02d}", 11, MUTED)
        n.text_frame.paragraphs[0].alignment = PP_ALIGN.RIGHT
    return s


def tb(s, l, t, w, h, text="", size=18, color=INK, bold=False,
       align=PP_ALIGN.LEFT, spacing=1.25, name=FONT):
    box = s.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        if not line:
            continue
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        _font(r, name)
    return box


def rule(s, l, t, w, color=ACCENT, h=0.045):
    sh = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t),
                            Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def chip(s, l, t, w, h, fill=WHITE, border=BORDER):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t),
                            Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = border
    sh.line.width = Pt(0.75)
    sh.shadow.inherit = False
    sh.adjustments[0] = 0.06
    return sh


def kicker(s, text, l=0.72, t=0.52):
    """小标签：朱红胶囊 + 大写小字"""
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t),
                             Inches(0.42 + 0.165 * len(text)), Inches(0.32))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xF8, 0xE6, 0xE0)
    box.line.fill.background()
    box.shadow.inherit = False
    box.adjustments[0] = 0.5
    box.text_frame.word_wrap = False
    p = box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.size = Pt(10.5)
    r.font.bold = True
    r.font.color.rgb = ACCENT
    _font(r)


def headline(s, text, t=0.92, size=31, w=11.9):
    tb(s, 0.72, t, w, 0.9, text, size, INK, True, spacing=1.15)


def note(s, text):
    NOTES.append(text)
    s.notes_slide.notes_text_frame.text = text


# ======================================================== 01 封面
s = slide()
rule(s, 0.72, 1.62, 1.05)
tb(s, 0.72, 1.9, 11.6, 1.5, "世界语言赛博活力图谱", 46, INK, True)
tb(s, 0.72, 3.05, 11.6, 0.6, "数字时代的语言生存图谱", 22, INK2)
tb(s, 0.72, 4.0, 11.6, 1.0,
   "什么样的语言，正在数字化的浪潮里被抛下？", 24, ACCENT, True)
tb(s, 0.72, 5.55, 6.0, 0.9,
   "数据可视化与人机交互\n学号 10002234　姓名 张某某", 14, MUTED, spacing=1.7)
tb(s, 8.6, 5.55, 4.1, 0.9,
   "157,736 行自采集数据\n6 个联动视图 · 4 类交互", 14, MUTED, align=PP_ALIGN.RIGHT,
   spacing=1.7)
note(s, "老师好，我做的题目是《世界语言赛博活力图谱》。"
        "一句话说，我想用可视化的方式回答一个问题：什么样的语言，"
        "正在数字化的浪潮里被抛下。")

# ======================================================== 02 问题
s = slide(2, "问题")
kicker(s, "一个更隐蔽的流失")
headline(s, "不是「内容少」，是根本不存在。")
tb(s, 0.72, 1.98, 11.5, 1.15,
   "全球约 7,000 种语言，能在维基百科上拥有独立入口的只有 267 种，"
   "占本数据集 2,662 门语言的 10.0%；其余 2,395 门在互联网上没有自己的入口。",
   17, INK2, spacing=1.5)
for i, (num, lab) in enumerate([("2,662", "门语言"), ("267", "有维基版本"),
                                ("10.0%", "数字在场率")]):
    x = 0.72 + i * 4.06
    chip(s, x, 3.5, 3.7, 1.55)
    tb(s, x + 0.3, 3.7, 3.1, 0.8, num, 44, ACCENT, True)
    tb(s, x + 0.3, 4.55, 3.1, 0.4, lab, 13, MUTED)
tb(s, 0.72, 5.45, 11.9, 1.1,
   "口语层面仍然健康的语言，在数字空间也可能一片空白 —— "
   "而它不会发出任何声响，没有任何报错。", 17, INK2, spacing=1.5)
note(s, "先看一个数字。全球约有七千种语言，但能在维基百科上拥有独立入口的只有 267 种，"
        "占我们数据集的 10%。剩下 2,395 种不是「内容少」，是根本不存在："
        "你在网上搜不到它，也搜不到关于它的任何持续更新的内容。"
        "这里的关键区别是——不是内容太少，是连一个可以持续更新的入口都没有。"
        "而这种缺席不会发出任何声响，没有任何报错。")

# ======================================================== 03 现实意义
s = slide(3, "现实意义")
kicker(s, "为什么这件事重要")
headline(s, "「网上有多少内容」，正在成为判断语言重要性的依据。")
cards = [
    ("语言政策", "网络使用状况已进入语言规划的评估指标；资料库越薄，越容易被判定为「不值得投入」。"),
    ("教育资源", "教材、课程、输入法、字幕，都优先供给有数字材料的那几十种语言。"),
    ("大模型语料", "训练数据直接按网页语种的多少分配，语料缺席的语言在模型里也几乎不存在。"),
]
for i, (h, d) in enumerate(cards):
    x = 0.72 + i * 4.13
    chip(s, x, 2.35, 3.78, 2.05)
    rule(s, x, 2.35, 3.78, ACCENT, 0.05)
    tb(s, x + 0.32, 2.62, 3.2, 0.45, h, 19, INK, True)
    tb(s, x + 0.32, 3.12, 3.15, 1.1, d, 13, INK2, spacing=1.55)
chip(s, 0.72, 4.78, 11.92, 1.15, SUBTLE)
tb(s, 1.05, 4.98, 11.3, 0.8,
   "缺席一旦发生，就同时发生在两个世界：数字世界里搜不到，政策视野里也随之消失。\n"
   "学术界把这种叠加称为「双重缺席」（double absence）。", 16, INK, spacing=1.6)
note(s, "这件事重要，是因为今天判断一种语言重不重要，越来越依赖它在网上有多少内容。"
        "语言政策要看网络使用状况，教育资源要看有没有可用的数字材料，"
        "大模型的训练语料更是直接按网页语种分配。"
        "一旦一种语言在数字空间缺席，它在政策视野里也随之消失——我们叫它双重缺席。"
        "所以这个项目要回答的不是「哪种语言快死了」——那是语言学的事；"
        "而是「哪种语言已经在网上消失了」，这是数据能回答的那一半。")

# ======================================================== 04 四个问题
s = slide(4, "研究问题")
kicker(s, "把大问题拆开")
headline(s, "四个可以被数据回答的问题")
qs = [
    ("01", "数字在场率有多低？", "2,662 门语言里，究竟有多少在互联网上存在？"),
    ("02", "十年里谁涨谁退？", "2015–2026 共 135 个月的浏览与编辑量。"),
    ("03", "两种活力是否一致？", "语言学的濒危程度，与数字关注度是对应的还是分裂的？"),
    ("04", "缺席是局部还是全局？", "是某几个语系的困境，还是整个语言生态的共同处境？"),
]
for i, (n, q, d) in enumerate(qs):
    y = 2.15 + i * 1.13
    tb(s, 0.72, y, 0.85, 0.6, n, 26, RGBColor(0xD8, 0xC8, 0xB8), True, name=MONO)
    tb(s, 1.62, y - 0.03, 5.0, 0.5, q, 19, INK, True)
    tb(s, 6.55, y, 6.0, 0.6, d, 14, INK2, spacing=1.45)
note(s, "为此我把问题拆成四个：数字在场率到底多低？十年里谁涨谁退？"
        "语言学的濒危程度和数字关注度是对应的还是分裂的？"
        "这种缺席是局部还是全局？")

# ======================================================== 05 数据
s = slide(5, "数据与方法")
kicker(s, "数据的价值在于「口径互不相干」")
headline(s, "五个来源，四套互不重叠的记录口径")
rows = [
    ("WALS Online", "语言结构地图集", "语法特征 · 坐标 · 语系", "2,662 × 192 → 76,475"),
    ("Wikimedia REST", "维基媒体接口", "月度浏览量 · 编辑量", "135 个月 → 65,161"),
    ("Glottolog", "语言谱系数据库", "濒危等级 · 描写深度 · 文献清单", "8,872 / 9,317 / 9,302"),
    ("Wikidata", "结构化知识库", "ISO 码映射 · 宏观语言 · 中文名", "185 / 5,761"),
    ("sitematrix", "维基站点列表", "每语言拥有哪些维基项目", "374 个语言版本"),
]
shape = s.shapes.add_table(len(rows) + 1, 4, Inches(0.72), Inches(2.12),
                           Inches(9.15), Inches(3.3))
tbl = shape.table
tbl.columns[0].width = Inches(2.15)
tbl.columns[1].width = Inches(2.05)
tbl.columns[2].width = Inches(2.95)
tbl.columns[3].width = Inches(2.0)
hdr = ("来源", "性质", "采集内容", "规模")
for c, h in enumerate(hdr):
    cell = tbl.cell(0, c)
    cell.text = ""
    cell.fill.solid()
    cell.fill.fore_color.rgb = SUBTLE
    p = cell.text_frame.paragraphs[0]
    r = p.add_run()
    r.text = h
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = INK
    _font(r)
for ri, row in enumerate(rows, start=1):
    for ci, v in enumerate(row):
        cell = tbl.cell(ri, ci)
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = WHITE
        p = cell.text_frame.paragraphs[0]
        r = p.add_run()
        r.text = v
        r.font.size = Pt(10.5)
        r.font.color.rgb = INK if ci == 0 else INK2
        r.font.bold = ci == 0
        _font(r)
chip(s, 10.2, 2.12, 2.44, 1.6)
tb(s, 10.45, 2.32, 2.0, 0.7, "157,736", 30, ACCENT, True)
tb(s, 10.45, 3.0, 2.0, 0.5, "行数据 · 9 张表", 12, MUTED)
chip(s, 10.2, 3.9, 2.44, 1.52, SUBTLE)
tb(s, 10.45, 4.1, 2.0, 1.2,
   "刻意选择不同学科的口径：只有一个结论在四套口径下都成立，才能排除单一数据集偏差。",
   12, INK, spacing=1.5)
note(s, "数据来自五个互不相干的来源：WALS 给语法结构，维基媒体给月度浏览与编辑量，"
        "Glottolog 给濒危等级和描写文献清单，Wikidata 和 UNESCO 补 ISO 映射与濒危名录，"
        "sitematrix 给每个语言拥有哪些维基项目。总共 15.7 万行、九张表。"
        "我刻意选择不同学科的口径，因为只有一个结论在四套口径下都成立，"
        "才能说明它不是某个数据集的偏差。"
        "采集本身也不轻松：两套语言代码标准要转换，宏观语言的码在 WALS 里根本不存在，"
        "还有七个维基版本的域名猜不出来。这些坑都写进了代码注释。")

# ======================================================== 06 系统全景
s = slide(6, "系统设计")
kicker(s, "换数据不需要改视图")
headline(s, "四层架构：采集 → 处理 → 可视化 → 交互", 0.92, 29)
im = s.shapes.add_picture(f"{FIG}/01-mindmap.png", Inches(0.72), Inches(1.95),
                          width=Inches(11.9))
tb(s, 0.72, 6.35, 11.9, 0.45,
   "四个层只通过同一份数据契约耦合：新增一个视图不需要修改任何已有模块。",
   13, MUTED)
note(s, "系统分四层：采集、处理、可视化、交互。"
        "分层的目的是让换数据不需要改视图，四个层只通过同一份数据契约耦合。")

# ======================================================== 07 六个视图
s = slide(7, "系统设计")
kicker(s, "共用一个状态仓库，任一处筛选全局同步")
headline(s, "六个视图，一条论证链", 0.92, 29)
shots = [
    ("03-map-density", "地图 · 在哪与谁还活着"),
    ("05-growth", "活力变化 · 谁在退"),
    ("06-matrix", "记录缺口 · 数据有多不可靠"),
    ("07-endanger", "濒危 × 关注 · 两种活力"),
    ("08-flow", "流向 · 往哪边走"),
    ("09-story", "故事模式 · 8 步引导"),
]
for i, (f, label) in enumerate(shots):
    col, row = i % 3, i // 3
    x = 0.72 + col * 4.05
    y = 2.05 + row * 2.3
    s.shapes.add_picture(f"{FIG}/{f}.png", Inches(x), Inches(y),
                         width=Inches(3.72))
    tb(s, x, y + 1.56, 3.72, 0.35, label, 11.5, INK2, align=PP_ALIGN.CENTER)
note(s, "六个视图共用一个状态仓库，任一处筛选全局同步。"
        "地图回答在哪里，活力变化回答谁在退，条件对比回答结构不同的语言处境是否不同，"
        "记录缺口这张最特殊——它不展示语言，展示的是数据本身有多不可靠；"
        "濒危与关注回答两种活力是否一致；流向用桑基图回答语言正往哪一边走。"
        "这六个视图不是六张独立的图，而是同一条论证链上的六步。")

# ======================================================== 08 创新 1
s = slide(8, "创新点 1")
kicker(s, "把「数据缺口」本身做成可视化对象")
headline(s, "先承认数据不完整，结论才站得住", 0.92, 29)
s.shapes.add_picture(f"{FIG}/06-matrix.png", Inches(0.72), Inches(2.0),
                     width=Inches(7.6))
tb(s, 8.62, 2.05, 4.0, 0.6, "15.0%", 40, ACCENT, True)
tb(s, 8.62, 2.7, 4.0, 0.5, "矩阵填充率", 13, MUTED)
for i, t in enumerate([
    "2,660 × 192 的矩阵只有 15% 的格子有值。",
    "纵轴不是一门语言，而是约 7 门语言的一条横带。",
    "同一列从上往下变浅，不是特征变了，\n而是「能回答这个问题的语言越来越少」。",
]):
    tb(s, 8.62, 3.3 + i * 1.05, 4.0, 1.0, t, 13, INK2, spacing=1.5)
note(s, "第一个创新点，是我把数据缺口本身做成了可视化对象。"
        "多数可视化只展示数据，但这一张展示的是数据有多不可靠："
        "WALS 的 2,660 乘 192 矩阵只有 15% 的格子有值。"
        "纵轴是语言按记录完整度排序后切成的 380 条横带，"
        "同一列从上往下变浅，不代表特征变了，而是能回答这个问题的语言越来越少。"
        "先把缺口摊开，后面的结论才站得住。")

# ======================================================== 09 创新 2
s = slide(9, "创新点 2")
kicker(s, "把「关系」落在同一个地理语境里")
headline(s, "语系星群：选中一门语言，画出它的家族", 0.92, 29)
s.shapes.add_picture(f"{FIG}/04-map-family.png", Inches(0.72), Inches(2.0),
                     width=Inches(7.6))
tb(s, 8.62, 2.1, 4.0, 1.3,
   "选中任何一门语言，地图上立刻出现三样东西：", 13.5, INK, True, spacing=1.5)
for i, t in enumerate([
    "从它放射到同语系每一门语言的连线",
    "该语系全部成员的外轮廓（凸包）",
    "连线那头的浅色底圈 —— 既不盖住颜色编码，又能认出「这些是一家」",
]):
    tb(s, 8.62, 3.35 + i * 0.92, 4.05, 0.9, "· " + t, 12.5, INK2, spacing=1.45)
chip(s, 8.62, 6.0, 4.05, 0.75, SUBTLE)
tb(s, 8.85, 6.12, 3.6, 0.6,
   "按需显现：默认不出现，所以没有增加视觉密度", 11.5, INK, spacing=1.4)
note(s, "第二个创新点是语系星群。选中任何一门语言，地图上立刻画出它所在语系的所有成员连线、"
        "外轮廓，和连线那头的浅色底圈。关系维度通常要另起一张网络图，"
        "我把它直接落在同一个地理语境里，而且按需出现，不会让默认视图变密。")

# ======================================================== 10 创新 3
s = slide(10, "创新点 3")
kicker(s, "方法论上的创新")
headline(s, "四套独立口径，交叉验证同一个结论", 0.92, 29)
rows = [("WALS 记录的特征数", 5.6, 92.9), ("Glottolog 描写深度", 0.0, 17.6),
        ("描写文献数", 2.5, 30.8), ("AES / UNESCO 濒危等级", 0.9, 18.0)]
tb(s, 0.72, 2.05, 3.2, 0.4, "口径", 11, MUTED, True)
tb(s, 4.2, 2.05, 5.0, 0.4, "从「最不受记录」到「记录最完整」的有维基比例", 11, MUTED, True)
for i, (name, lo, hi) in enumerate(rows):
    y = 2.55 + i * 1.0
    tb(s, 0.72, y + 0.02, 3.35, 0.45, name, 14, INK, True)
    track = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.25),
                               Inches(y + 0.09), Inches(6.4), Inches(0.26))
    track.fill.solid()
    track.fill.fore_color.rgb = RGBColor(0xEE, 0xE9, 0xDF)
    track.line.fill.background()
    track.shadow.inherit = False
    track.adjustments[0] = 0.5
    w = 6.4 * (hi - lo) / 100.0
    bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                             Inches(4.25 + 6.4 * lo / 100.0), Inches(y + 0.09),
                             Inches(max(w, 0.12)), Inches(0.26))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()
    bar.shadow.inherit = False
    bar.adjustments[0] = 0.5
    tb(s, 10.85, y + 0.02, 1.9, 0.45,
       f"{lo:.1f}% → {hi:.1f}%", 12, INK2, name=MONO)
tb(s, 0.72, 6.35, 11.9, 0.5,
   "四套口径、同一个方向 —— 这排除了「结论只是某一个数据集偏差」的可能。",
   14, ACCENT, True)
note(s, "第三个创新点是方法论上的：四套独立口径交叉验证。"
        "WALS 记录的特征数，从 5.6% 到 92.9%；Glottolog 的描写深度，0 到 17.6%；"
        "描写文献数，2.5 到 30.8%；濒危等级，0.9 到 18%。"
        "四套口径、同一个方向。这是我认为最抗问的一点，"
        "因为它排除了结论只是某一个数据集偏差的可能。")

# ======================================================== 11 创新 4
s = slide(11, "创新点 4")
kicker(s, "高阶人机交互")
headline(s, "三件交互：一句话提问、故事模式、画面即链接", 0.92, 27)
s.shapes.add_picture(f"{FIG}/09-story.png", Inches(7.6), Inches(2.0),
                     width=Inches(5.05))
items = [
    ("自然语言提问", "底部输入一句话 → 结构化意图 → 写入状态仓库 → 全视图联动。"
                     "本地规则优先（不联网可用），复杂问法交给大模型，"
                     "返回严格 JSON，不让模型输出直接污染状态。"),
    ("故事模式", "8 步线性叙事，每步自动切换视图与筛选。"
                 "文案里的数字全部实时计算 —— 数据一更新，它不会变成假话。"),
    ("URL 状态分享", "当前画面编码进地址栏，18 个字段。"
                     "两个条件的链接只有 17 个字符：?area=Africa&end=5"),
]
for i, (h, d) in enumerate(items):
    y = 2.05 + i * 1.45
    tb(s, 0.72, y, 6.5, 0.42, h, 17, ACCENT, True)
    tb(s, 0.72, y + 0.4, 6.55, 1.0, d, 12.5, INK2, spacing=1.5)
note(s, "交互上做了三件：底部可以用一句话提问，本地规则优先、大模型兜底；"
        "故事模式把结论串成 8 步引导，文案里的数字全部实时计算，数据一更新它不会变成假话；"
        "以及当前画面可以编码进 URL 直接分享。")

# ======================================================== 12 发现的规律
s = slide(12, "发现的规律")
kicker(s, "四条结论")
headline(s, "被记录得越少，越可能在网上不存在", 0.92, 31)
finds = [
    ("10.0%", "数字在场率", "2,662 门语言里只有 267 门有维基百科版本"),
    ("4 / 4", "口径一致", "四套互不相干的记录口径，全部指向同一方向"),
    ("89.9%", "全局而非局部", "逐个检查语言数 ≥20 的 15 个语系，每个都是「无维基」占多数"),
    ("+2003%", "但数字空间也在续命", "已灭绝的康沃尔语十年增长 2003%，马恩岛语 +116%"),
]
for i, (num, title, desc) in enumerate(finds):
    y = 2.1 + i * 1.18
    chip(s, 0.72, y - 0.12, 11.92, 1.02, WHITE if i % 2 == 0 else SUBTLE)
    tb(s, 0.95, y + 0.02, 2.0, 0.55, num, 26, ACCENT, True)
    tb(s, 3.15, y + 0.06, 2.6, 0.5, title, 15, INK, True)
    tb(s, 5.95, y + 0.08, 6.5, 0.7, desc, 13, INK2, spacing=1.4)
note(s, "最后是发现的规律。第一，在场率只有 10%。"
        "第二，四套口径同向：被记录得越少，越可能在网上不存在。"
        "第三，这是全局性的——全局 89.9% 没有维基版本，"
        "而逐个检查语言数不少于 20 的 15 个语系，每一个都是无维基占多数，"
        "不是某几个语系的问题。"
        "第四，也是最反直觉的一条：已灭绝档的 223 门语言里只有 2 门有维基版本，"
        "而这 2 门正是康沃尔语和马恩岛语——它们的口语已经消失，"
        "数字关注度却在十年里分别涨了 2003% 和 116%。"
        "这两门语言作为口语都已经消失，一个在 1777 年、一个在 1974 年，"
        "但在数字空间里反而在增长。所以数字空间既能抛弃一种语言，也能替它续命。"
        "这也回答了最开始那个问题：被抛下的不是「快要消失的语言」，"
        "而是「从来没有被记录过的语言」。")

# ======================================================== 13 结论
s = slide(13, "结论与局限")
kicker(s, "一句话结论 + 三条诚实的局限")
headline(s, "缺席是全局性的，但它不是单向的漏斗", 0.92, 29)
chip(s, 0.72, 2.1, 11.92, 1.25, SUBTLE)
tb(s, 1.02, 2.3, 11.3, 0.9,
   "被记录得越少的语言，在数字世界里也越可能根本不存在；这种缺席不分语系。\n"
   "但康沃尔语与马恩岛语说明：数字空间也能替一门语言续命。", 16, INK, spacing=1.65)
tb(s, 0.72, 3.65, 5.9, 0.45, "已知局限", 15, ACCENT, True)
for i, t in enumerate([
    "「活力」只能用维基百科代理：212 门有濒危等级却无维基版本的语言，"
    "可能只是「没人写维基」，而不是「没人说」。",
    "维基百科本身有系统性偏差，偏向有写作传统与网络接入的语言。",
    "WALS 有把两种语言合并在一个条目的情况（如索布语），任何单一选择都是折中。",
]):
    tb(s, 0.72, 4.2 + i * 0.78, 5.95, 0.75, "· " + t, 12, INK2, spacing=1.45)
tb(s, 6.95, 3.65, 5.7, 0.45, "展望", 15, ACCENT, True)
for i, t in enumerate([
    "接入濒危语言目录（ELCat）的资源清单与 EGIDS 分级，把「数字在场」扩展到维基百科之外。",
    "用语言家族树或力导向网络进一步表达语系结构。",
    "把分析扩展成可交互的假设检验工具，让使用者自己验证两个指标是否相关。",
]):
    tb(s, 6.95, 4.2 + i * 0.78, 5.7, 0.75, "· " + t, 12, INK2, spacing=1.45)
note(s, "结论一句话：被记录得越少的语言，在数字世界里也越可能根本不存在，"
        "而且这种缺席不分语系。局限也说清楚：活力只能用维基百科代理，"
        "可能只是没人写维基而不是没人说；维基百科本身偏向有写作传统和网络接入的语言；"
        "WALS 有把两种语言合并的情况。后续想接入 ELCat 的资源清单，把数字在场扩展到维基百科之外。")

# ======================================================== 14 谢谢
s = slide()
rule(s, 0.72, 2.55, 1.05)
tb(s, 0.72, 2.85, 11.6, 1.0, "谢谢老师", 42, INK, True)
tb(s, 0.72, 3.95, 11.6, 0.55,
   "代码、数据与 17 个可独立运行的验证脚本全部开源", 16, INK2)
tb(s, 0.72, 4.85, 11.6, 0.5,
   "github.com/quvro/world-language-vitality-map", 15, ACCENT, name=MONO)
tb(s, 0.72, 5.3, 11.6, 0.5, "在线演示  http://127.0.0.1:5173/", 14, MUTED)
note(s, "代码和全部数据都在这个仓库里，谢谢老师。")

prs.save("paper/世界语言赛博活力图谱_答辩PPT.pptx")
print(f"已生成 PPT：{len(prs.slides)} 页")
print(f"讲稿总字数：{sum(len(n) for n in NOTES)} 字")
for i, n in enumerate(NOTES, 1):
    print(f"  第 {i:02d} 页  {len(n):3d} 字  {n[:34]}…")
