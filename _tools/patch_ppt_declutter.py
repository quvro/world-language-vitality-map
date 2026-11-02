"""在 PPT 第三部分插入一页「字形抗拥挤算法」，位置紧跟在复合字形之后。

第三部分现在是「视图与功能」逐页展开，字形那页只讲了五个部件，
算法本身（屏幕空间贪心抽稀）没有落脚点。这一页补上。
"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

if "字形抗拥挤" in s:
    print("  已插入过，跳过")
    raise SystemExit(0)

# ---- 1) 19 及之后整体后移一位
def bump(m):
    n = int(m.group(2))
    return f"{m.group(1)}({n + 1}," if n >= 19 else m.group(0)

s, c = re.subn(r"\b(slide|divider)\((\d+),", bump, s)
print(f"  ok   页码后移 {c} 处")

# ---- 2) 找到「语言体检单」那一页的起点，插在它之前
loc = s.find('kicker(s, "功能 · 语言体检单")')
if loc < 0:
    print("  MISS 找不到体检单页")
    raise SystemExit(1)
start = s.rfind("s = slide(", 0, loc)
start = s.rfind("\n", 0, start) + 1

BLOCK = '''# ============================================ 19 字形抗拥挤（算法）
s = slide(19, "三、视图与功能")
kicker(s, "算法 · 屏幕空间贪心抽稀")
headline(s, "2,662 个字形，怎么不糊成一片", 0.92, 30)
for i, (h, d) in enumerate([
    ("排序", "按「半径 × 不透明度」降序。越大越显眼的先占位，"
             "保证重要语言不会被旁边的小点挤掉。"),
    ("落格", "按屏幕坐标放进 26px 的哈希格。查位是 O(1)，"
             "不必让 2,662 个字形两两比较。"),
    ("判冲突", "插入前只查 3×3 邻域：与已放置字形距离小于半径和 × 0.82，"
               "就跳过并返回空 group。"),
    ("判新一轮", "ECharts 每轮绘制都从 dataIndex 0 开始 —— "
                 "用它判定新一轮并清空占位表，不需要监听事件。"),
]):
    y = 1.98 + i * 1.16
    tb(s, 0.72, y - 0.06, 0.46, 0.44, str(i + 1), 21, ACCENT, True)
    tb(s, 1.34, y, 4.6, 0.4, h, 15.5, INK, True)
    tb(s, 1.34, y + 0.42, 5.5, 0.68, d, 11.5, INK2, spacing=1.5)
s.shapes.add_picture(f"{FIG}/20-glyph.png", Inches(7.25), Inches(1.98),
                     width=Inches(5.45))
tb(s, 7.25, 5.55, 5.45, 0.5, "抽稀后：字距拉开，大小层次保留",
   11, MUTED)
rect(s, 0.72, 6.46, 11.9, 0.72, SUBTLE, radius=0.1)
tb(s, 0.95, 6.58, 11.4, 0.5,
   "关键取舍：判定放在屏幕空间而不是经纬度 —— 缩放后字距自然拉开，抽稀自动放松，"
   "于是不必监听 roam，也就避开了「重绘与漫游动画打架导致地图错位」那个坑。",
   11.5, INK, spacing=1.4)
note(s, "这一页讲字形怎么不糊成一片。四个字：排、落、判、重。"
        "先按大小排序，重要的先占位；再按屏幕坐标落进 26 像素的哈希格；"
        "插入前只查周围九格，太挤就跳过；ECharts 每轮绘制都从第 0 个数据开始，"
        "用这个信号清空占位表，不用监听任何事件。"
        "为什么用屏幕坐标而不是经纬度：放大之后字距自然会拉开，抽稀就自动放松了，"
        "所以我完全不用管地图漫游 —— 之前正是因为重绘和漫游动画打架，地图才会错位。")

'''

s = s[:start] + BLOCK + s[start:]
io.open(P, "w", encoding="utf-8").write(s)
print("  ok   已插入第 19 页（字形抗拥挤）")
