"""生成论文用的两张结构图：系统架构图、数据处理流程图。

为什么用代码画而不是生图：这两张是结构图，节点数固定、文字必须准确，
生图模型会把 157,736 写成 157.738、五个来源画成四个、连线接错层。
代码画的另一个好处是：改一个数字重跑即可，风格与论文其余图一致。

配色（低饱和，语义固定）：
    砖红 #B5564F = 输入    灰蓝 #4A6E8A = 处理
    苔绿 #6E8B6B = 输出    暖灰 #8C8880 = 中性
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.patches import Ellipse, Polygon
from matplotlib.font_manager import FontProperties, findSystemFonts
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "paper" / "figs"

RED = "#B5564F"
BLUE = "#4A6E8A"
GREEN = "#6E8B6B"
GRAY = "#8C8880"
INK = "#3E3A34"
INK2 = "#6B655C"
LINE = "#D9D5CC"
BG = "#FAF8F4"


def pick_cjk_font() -> str:
    """找一个能渲染中文的字体。Windows 上优先微软雅黑。"""
    prefer = ["Microsoft YaHei", "MSYH", "SimHei", "Noto Sans CJK SC",
              "Source Han Sans SC", "PingFang SC", "Heiti SC"]
    names = set()
    for p in findSystemFonts():
        names.add(Path(p).stem)
    for want in prefer:
        for n in names:
            if want.lower().replace(" ", "") in n.lower().replace(" ", ""):
                print(f"  中文字体: {n}")
                return n
    # 退一步：直接试常见文件名
    for cand in ("msyh.ttc", "simhei.ttf", "msyh.ttf"):
        for p in findSystemFonts():
            if Path(p).name.lower() == cand:
                print(f"  中文字体(按文件名): {p}")
                return FontProperties(fname=p).get_name()
    print("  !! 没找到中文字体，将退回默认字体（中文会显示成方块）")
    return "DejaVu Sans"


CJK = pick_cjk_font()
plt.rcParams["font.sans-serif"] = [CJK, "DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def canvas(w: float, h: float, xr: tuple[float, float], yr: tuple[float, float]):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(*xr)
    ax.set_ylim(*yr)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def box(ax, x, y, w, h, *, edge=LINE, face="none", lw=1.0, r=1.2, z=2):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        linewidth=lw, edgecolor=edge, facecolor=face, zorder=z,
    )
    ax.add_patch(p)
    return p


def txt(ax, x, y, s, *, size=9, color=INK, weight="normal", ha="left",
        va="center", rot=0, family=None, z=5):
    return ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                   ha=ha, va=va, rotation=rot, zorder=z,
                   family=family or CJK)


def arrow(ax, x1, y1, x2, y2, *, color=GRAY, lw=0.9, style="-|>"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=8,
        linewidth=lw, color=color, shrinkA=0, shrinkB=0, zorder=3,
    ))


def thumb(ax, name: str, x, y, w, h, *, crop=(0.06, 0.14, 0.94, 0.86)):
    """把已有截图的图表区域裁一小块贴进来，作为"小图片说明"。"""
    p = FIG / f"{name}.png"
    if not p.exists():
        print(f"  !! 缺少截图 {p.name}")
        return
    im = Image.open(p).convert("RGB")
    W, H = im.size
    im = im.crop((int(W * crop[0]), int(H * crop[1]),
                  int(W * crop[2]), int(H * crop[3])))
    ax.imshow(im, extent=(x, x + w, y, y + h), zorder=4, aspect="auto")
    ax.add_patch(Rectangle((x, y), w, h, linewidth=0.8, edgecolor=LINE,
                           facecolor="none", zorder=5))


# =====================================================================
# 图 A：系统架构
# =====================================================================
def fig_architecture():
    fig, ax = canvas(16, 10, (0, 160), (0, 100))

    txt(ax, 3, 96, "世界语言赛博活力图谱 · 系统架构", size=13, weight="bold")
    txt(ax, 3, 92, "四层只通过同一份数据契约耦合：新增一个视图不需要修改任何已有模块",
        size=8.5, color=INK2)

    bands = [
        (76, "数据来源", "DATA SOURCES"),
        (56, "处理", "PIPELINE"),
        (36, "应用", "APPLICATION"),
        (16, "交互", "INTERACTION"),
    ]
    for y, zh, en in bands:
        txt(ax, 2.5, y + 7, zh, size=10, weight="bold", rot=90, ha="center")
        txt(ax, 6.2, y + 7, en, size=6.6, color=INK2, rot=90, ha="center")

    # ---- 第一层：五个来源
    srcs = [
        ("WALS CLDF", "76,475 行", "2,662 × 192 特征"),
        ("Wikimedia REST", "65,161 行", "135 个月"),
        ("Glottolog CLDF", "27,291 行", "濒危/深度/文献"),
        ("Wikidata SPARQL", "ISO 对齐", "P1999 / P279"),
        ("Wikimedia 站点表", "374 个版本", "各语言维基"),
    ]
    x0, bw, gap = 24, 24, 2.2
    for i, (name, n, sub) in enumerate(srcs):
        x = x0 + i * (bw + gap)
        box(ax, x, 76, bw, 14, edge=RED, face=matplotlib.colors.to_rgba(RED, 0.07))
        txt(ax, x + 1.6, 86.6, name, size=8.2, weight="bold")
        txt(ax, x + 1.6, 83.4, n, size=9.2, color=RED, weight="bold",
            family="monospace")
        txt(ax, x + 1.6, 79.6, sub, size=7.0, color=INK2)
        arrow(ax, x + bw / 2, 75.6, x + bw / 2, 70.6, color=RED)

    # ---- 第二层：处理
    box(ax, 24, 56, 131.5, 14, edge=BLUE,
        face=matplotlib.colors.to_rgba(BLUE, 0.07))
    txt(ax, 26.2, 67.4, "7 个幂等脚本 · 实体对齐 · SQLite 9 张表 / 157,736 行",
        size=9.4, weight="bold")
    txt(ax, 26.2, 64.0,
        "重跑结果一致：可复现是这份数据能被检验的前提", size=7.4, color=INK2)

    # 三方映射小节点
    hub_x, hub_y = 72, 60.0
    ax.add_patch(Ellipse((hub_x, hub_y), 1.6, 1.6, color=BLUE, zorder=6))
    pills = [("WALS 码", 84, 62.4), ("Glottocode", 92, 60.0), ("ISO 639-3", 84, 57.6)]
    for label, px, py in pills:
        w = 2.6 + len(label) * 0.78
        box(ax, px, py - 1.9, w, 3.8, edge=BLUE, lw=0.8, r=1.9, z=4)
        txt(ax, px + w / 2, py, label, size=7.2, ha="center", z=6)
        ax.plot([hub_x + 0.9, px], [hub_y, py], color=BLUE, lw=0.8, zorder=3)
    txt(ax, 84, 55.0, "一门语言，三套编号", size=6.8, color=INK2)

    # ---- 第三层：应用
    box(ax, 24, 36, 131.5, 14, edge=GREEN,
        face=matplotlib.colors.to_rgba(GREEN, 0.08))
    txt(ax, 26.2, 47.4, "一份 JSON 契约 → Vue 3 + Pinia 单一状态仓库", size=9.4,
        weight="bold")
    chips = ["地图", "活力变化", "条件对比", "记录缺口", "濒危 × 关注", "流向"]
    cx = 26.2
    for c in chips:
        w = 2.4 + len(c) * 1.28
        box(ax, cx, 41.4, w, 3.4, edge=GREEN, lw=0.7, r=1.0, z=4)
        txt(ax, cx + w / 2, 43.1, c, size=7.0, ha="center", z=6)
        cx += w + 1.2
    chips2 = ["复合字形", "语言体检单", "大模型问答"]
    cx = 26.2
    for c in chips2:
        w = 2.4 + len(c) * 1.28
        box(ax, cx, 37.2, w, 3.0, edge=GREEN, lw=0.7, r=1.0, z=4)
        txt(ax, cx + w / 2, 38.7, c, size=7.0, ha="center", z=6)
        cx += w + 1.2
    txt(ax, 130, 38.7, "6 视图 + 3 功能", size=7.0, color=GREEN, ha="right")
    arrow(ax, 90, 55.6, 90, 50.6, color=BLUE)

    # ---- 第四层：交互
    box(ax, 24, 16, 76, 12, edge=GRAY,
        face=matplotlib.colors.to_rgba(GRAY, 0.06))
    txt(ax, 26.2, 25.4, "交互层", size=9.4, weight="bold")
    acts = ["联动筛选（任一处改动全局同步）", "指向即解释（悬停给口径）",
            "故事模式（8 步线性叙事）", "URL 状态 / 自然语言提问"]
    for i, a in enumerate(acts):
        col, row = i % 2, i // 2
        txt(ax, 26.2 + col * 37, 21.4 - row * 3.4, "· " + a, size=7.4, color=INK2)
    arrow(ax, 60, 35.6, 60, 28.6, color=GREEN)

    # ---- 右下：三张小截图
    txt(ax, 104, 29.4, "视图示例", size=7.2, color=INK2)
    tw, th, ty = 14.6, 9.1, 17.6
    for i, name in enumerate(("03-map-density", "06-matrix", "08-flow")):
        thumb(ax, name, 104 + i * (tw + 1.2), ty, tw, th)
    txt(ax, 104, 15.2, "地图 · 记录缺口 · 流向（缩略）", size=6.6, color=INK2)

    out = FIG / "01-mindmap.png"
    fig.savefig(out, dpi=200, facecolor=BG)
    plt.close(fig)
    print(f"  已生成 {out.name}")


# =====================================================================
# 图 B：数据处理流程
# =====================================================================
def fig_pipeline():
    fig, ax = canvas(16, 10, (0, 160), (0, 100))

    txt(ax, 3, 96, "数据处理流程", size=13, weight="bold")
    txt(ax, 3, 92, "五个公开来源 → 7 个幂等脚本 → 9 张表 → 一份 JSON 契约",
        size=8.5, color=INK2)

    # 根
    box(ax, 3, 44, 19, 16, edge=RED, face=matplotlib.colors.to_rgba(RED, 0.07))
    txt(ax, 4.6, 56.0, "5 个公开来源", size=9.0, weight="bold")
    txt(ax, 4.6, 51.6, "157,736 行", size=10.5, color=RED, weight="bold",
        family="monospace")
    txt(ax, 4.6, 47.4, "9 张表 · SQLite", size=7.0, color=INK2)

    # 五个来源
    items = [("WALS CLDF", "76,475"), ("Wikimedia REST", "65,161"),
             ("Glottolog CLDF", "27,291"), ("Wikidata SPARQL", "ISO 对齐"),
             ("Wikimedia 站点表", "374")]
    ys = [88, 76, 64, 52, 40]
    for (name, n), y in zip(items, ys):
        box(ax, 28, y - 4.4, 34, 8.8, edge=LINE)
        txt(ax, 29.6, y + 1.4, name, size=8.0, weight="bold")
        txt(ax, 29.6, y - 2.2, n, size=7.4, color=RED, family="monospace")
        arrow(ax, 22.4, 52, 27.6, y, color=RED, lw=0.8)

    # 主轴
    box(ax, 68, 22, 16, 72, edge=BLUE, face=matplotlib.colors.to_rgba(BLUE, 0.06))
    segs = [("抓取", "7 个脚本\n幂等"), ("清洗", "实体对齐\n逐条核对"),
            ("聚合", "月度序列\n基线标记")]
    for i, (h, d) in enumerate(segs):
        cy = 82 - i * 24
        txt(ax, 76, cy, h, size=9.4, weight="bold", ha="center")
        txt(ax, 76, cy - 6.4, d, size=7.0, color=INK2, ha="center")
        if i < 2:
            ax.plot([68, 84], [cy - 10.6, cy - 10.6], color=LINE, lw=0.8)
    for y in ys:
        arrow(ax, 62.4, y, 67.6, min(max(y, 26), 90), color=BLUE, lw=0.8)

    # 强调：三方映射
    box(ax, 90, 70, 56, 18, edge=BLUE, lw=1.1,
        face=matplotlib.colors.to_rgba(BLUE, 0.05))
    txt(ax, 92, 85.0, "清洗的核心：实体对齐", size=8.6, weight="bold", color=BLUE)
    hub = (99, 79.0)
    ax.add_patch(Ellipse(hub, 1.4, 1.4, color=BLUE, zorder=6))
    for label, px, py in [("WALS 码", 106, 81.6), ("Glottocode", 116, 79.0),
                          ("ISO 639-3", 106, 76.4)]:
        w = 2.4 + len(label) * 0.8
        box(ax, px, py - 1.7, w, 3.4, edge=BLUE, lw=0.8, r=1.7, z=4)
        txt(ax, px + w / 2, py, label, size=7.0, ha="center", z=6)
        ax.plot([hub[0] + 0.8, px], [hub[1], py], color=BLUE, lw=0.8, zorder=3)
    txt(ax, 92, 73.0, "一门语言三套编号；一个小语种可能被多个维基版本认领",
        size=6.8, color=INK2)

    # 数据库
    cx, cy, dw, dh = 104, 52, 28, 12
    ax.add_patch(Rectangle((cx, cy), dw, dh, facecolor="none",
                           edgecolor=GRAY, linewidth=1.0, zorder=3))
    ax.add_patch(Ellipse((cx + dw / 2, cy + dh), dw, 3.2, facecolor=BG,
                         edgecolor=GRAY, linewidth=1.0, zorder=4))
    txt(ax, cx + dw / 2, cy + 5.6, "SQLite · 9 张表", size=8.6, weight="bold",
        ha="center")
    txt(ax, cx + dw / 2, cy + 2.4, "157,736 行", size=8.0, color=GRAY,
        ha="center", family="monospace")
    arrow(ax, 84.4, 58, 103.4, 58, color=BLUE)

    # 三个 JSON
    js = [("languages.json", "0.9 MB"), ("digital_presence.json", "2.2 MB"),
          ("feature_matrix.json", "4.9 MB")]
    for i, (n, sz) in enumerate(js):
        y = 36 - i * 9.4
        box(ax, 90, y, 50, 7.4, edge=LINE)
        txt(ax, 91.6, y + 4.6, n, size=7.6, family="monospace")
        txt(ax, 138, y + 4.6, sz, size=7.2, color=INK2, ha="right",
            family="monospace")
        arrow(ax, 118, 46.4 if i == 0 else y + 7.4, 118, y + 7.4, color=GRAY, lw=0.7)

    # 契约
    box(ax, 90, 10, 50, 10, edge=GREEN, face=matplotlib.colors.to_rgba(GREEN, 0.08))
    txt(ax, 91.6, 16.6, "一份 JSON 契约 → Pinia 状态仓库", size=8.8, weight="bold")
    txt(ax, 91.6, 12.8, "换数据不用改视图", size=7.2, color=INK2)
    arrow(ax, 115, 26.0, 115, 20.6, color=GREEN)

    # 小截图：稀疏矩阵
    txt(ax, 92, 7.4, "记录缺口矩阵（15.0% 填充率）", size=6.8, color=INK2)
    thumb(ax, "06-matrix", 124, 0.6, 18, 7.0, crop=(0.16, 0.30, 0.86, 0.88))

    out = FIG / "02b-pipeline.png"
    fig.savefig(out, dpi=200, facecolor=BG)
    plt.close(fig)
    print(f"  已生成 {out.name}")


if __name__ == "__main__":
    fig_architecture()
    fig_pipeline()
