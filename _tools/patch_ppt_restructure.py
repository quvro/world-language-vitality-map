"""重构 PPT 二、三两部分。

用户要求：二讲「系统架构 / 数据来源 / 搭建过程」，三「详细讲解视图与功能」。
原先第二部分缺"搭建过程"，第三部分标题是"四个创新点"，与要求不符。

做法：
  1) 二新增一页「搭建过程」（四步：抓取 → 清洗 → 建库 → 前端）
  2) 原 12 页及之后整体后移一位
  3) 三的标题从「四个创新点」改为「视图与功能」，页脚同步
  4) 各页 kicker 从"创新点 N"改为"视图 / 功能 / 方法论 / 交互"
"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

if "搭建过程" in s:
    print("  已改过，跳过")
    raise SystemExit(0)

# ---- 1) 12 及之后整体后移一位
def bump(m):
    n = int(m.group(2))
    return f"{m.group(1)}({n + 1}," if n >= 12 else m.group(0)

s, c = re.subn(r"\b(slide|divider)\((\d+),", bump, s)
print(f"  ok   页码后移 {c} 处")

# ---- 2) 插入「搭建过程」在第 12 位（三的 divider 之前）
BUILD = '''# ============================================================ 12 搭建过程
s = slide(12, "二、数据与系统")
kicker(s, "四步，全部可复现")
headline(s, "搭建过程：从公开接口到一份数据契约", 0.92, 29)
for i, (h, d) in enumerate([
    ("① 抓取", "5 个公开来源，7 个脚本。WALS / Glottolog 走 CLDF 与 CSV，"
               "维基走 REST 与 sitematrix，Wikidata 走 SPARQL。"),
    ("② 清洗", "最麻烦的是实体对齐：同一门语言在三套体系里分别是 WALS 码、"
               "Glottocode、ISO 639-3。以 Glottolog 为枢纽做映射，冲突逐条人工核对。"),
    ("③ 建库", "汇入 SQLite，9 张表、157,736 行。维表与事实表分离，"
               "前端只读导出的 JSON。"),
    ("④ 前端", "Vue 3 + Pinia，一份状态仓库驱动全部视图。"
               "四个层只通过同一份数据契约耦合。"),
]):
    y = 1.95 + i * 1.22
    tb(s, 0.72, y, 1.5, 0.45, h, 17, ACCENT, True)
    tb(s, 2.2, y - 0.02, 10.4, 1.0, d, 13, INK2, spacing=1.5)
    if i < 3:
        rect(s, 0.72, y + 1.02, 11.9, 0.012, RGBColor(0xE8, 0xE2, 0xD6))
tb(s, 0.72, 6.62, 11.9, 0.4,
   "7 个采集脚本都是幂等的：重跑结果一致，可复现是这份数据能被检验的前提。",
   12.5, MUTED)
note(s, "这一页讲怎么搭出来的，四步。抓取用了五个公开来源、七个脚本。"
        "最费劲的其实是第二步清洗：同一门语言在 WALS、Glottolog、ISO 三套体系里"
        "各有各的编号，我以 Glottolog 为枢纽做映射，冲突逐条人工核对。"
        "之后汇入 SQLite，九张表、十五万多行。前端只读导出的 JSON，"
        "四个层只通过同一份数据契约耦合，所以换数据不用改视图。"
        "七个脚本都是幂等的，重跑结果一致——可复现是数据能被检验的前提。")

'''

anchor = "# ============================================================ 13 章节三"
if anchor not in s:
    # 后移之后三的 divider 变成 13
    m = re.search(r"# =+ \d+ 章节三", s)
    anchor = m.group(0) if m else None
if anchor is None:
    print("  MISS 找不到三的章节标记")
    raise SystemExit(1)

s = s.replace(anchor, BUILD + anchor, 1)
print("  ok   已插入「搭建过程」")

# ---- 3) 三的标题与页脚
s = s.replace('divider(13, "三、四个创新点"', 'divider(13, "三、视图与功能"')
s = s.replace('"两个表现手法上的，两个方法论上的"', '"七个视图一个一个讲：它们各自回答什么问题、怎么读"')
s = s.replace('"三、四个创新点")', '"三、视图与功能")')
s = s.replace('"第三部分，也是我最想讲的部分：四个创新点。"',
              '"第三部分，把七个视图和它们承载的功能逐个讲一遍。"')
print("  ok   三的标题与页脚已改")

# ---- 4) kicker 逐个改写
PAIRS = [
    ("创新点 1 · 把「数据缺口」本身做成可视化对象",
     "视图 · 记录缺口：把「数据缺口」本身做成可视化对象"),
    ("创新点 2 · 把「关系」落在同一个地理语境里",
     "功能 · 语系星群：把「关系」落在同一个地理语境里"),
    ("创新点 3 · 方法论上的创新", "方法论 · 四套口径的秩相关检验"),
    ("创新点 4 · 高阶人机交互", "交互 · 三件交互"),
]
for a, b in PAIRS:
    if a in s:
        s = s.replace(a, b, 1)
        print(f"  ok   kicker {a[:12]}…")

# 「创新点 · 进阶」出现三次，按出现顺序分别改写
for new in ("视图 · 复合字形", "功能 · 语言体检单", "功能 · 大模型问答"):
    s = s.replace('kicker(s, "创新点 · 进阶")', f'kicker(s, "{new}")', 1)

io.open(P, "w", encoding="utf-8").write(s)
print("  已写回")
