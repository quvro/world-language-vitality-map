"""重写 PPT 第四部分：规律与结论 → 结论与展望。

用户要求三块：
  1) 从数据中分析出的规律 + 一两个有趣的小例子
  2) 目前的不足与下一步的方向
  3) 参考文献

原来是 3 个内容页，现在改成 4 个：规律 / 例子 / 不足与展望 / 参考文献。
"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

if "四、结论与展望" in s:
    print("  已改过，跳过")
    raise SystemExit(0)

# ---- 定位：四的 divider 到 End 之前
m = re.search(r'(?m)^# [=\s]*\d+ 章节四.*$', s)
if not m:
    m = re.search(r'(?m)^s = divider\(\d+, "四、规律与结论".*$', s)
if not m:
    print("  MISS 找不到四的章节标记")
    raise SystemExit(1)
start = m.start()

end_m = re.search(r'(?m)^# [=\s]*\d+ End.*$', s)
if not end_m:
    print("  MISS 找不到 End 标记")
    raise SystemExit(1)
end = end_m.start()

old = s[start:end]
print(f"  将替换 {len(old)} 字符（{old.count('slide(') - 1} 个内容页）")

NEW = '''# ============================================================ 22 章节四
s = divider(22, "四、结论与展望", "04", "四条规律、两个小例子、三点不足")
note(s, "最后一部分：我从数据里读出了什么，哪里还不足。")

# ============================================================ 23 四条规律
s = slide(23, "四、结论与展望")
kicker(s, "规律 · 从数据里读出来的")
headline(s, "四条规律，一条比一条更硬", 0.92, 30)
stats = [
    ("10.0%", "数字在场率", "2,662 门语言里只有 267 门有维基版本。"),
    ("8/8", "四套口径同向", "秩相关 8 对全部显著同向，|ρ| = 0.05–0.32；"
                            "彼此独立却方向一致。"),
    ("15 / 15", "缺席是全局的", "语言数 ≥ 20 的 15 个语系，无一例外都是多数语言没有维基。"),
    ("2 门", "但不是单向漏斗", "濒危等级最高的那一档里，仍有 2 门在数字空间里活着。"),
]
for i, (n, h, d) in enumerate(stats):
    col, row = i % 2, i // 2
    x = 0.72 + col * 6.15
    y = 1.98 + row * 2.28
    rect(s, x, y, 5.85, 2.0, SUBTLE, radius=0.12)
    tb(s, x + 0.32, y + 0.22, 2.6, 0.6, n, 30, ACCENT, True, name=MONO)
    tb(s, x + 2.95, y + 0.30, 2.7, 0.5, h, 13, INK, True)
    tb(s, x + 0.32, y + 0.98, 5.2, 0.85, d, 11.5, INK2, spacing=1.5)
note(s, "四条规律。第一，数字在场率只有百分之十，两千六百多门语言里只有二百六十七门"
        "有维基版本。第二，四套互不相干的口径方向一致——我算了秩相关，八对全部显著同向。"
        "第三，这种缺席是全局性的：语言数不少于二十的十五个语系，无一例外都是多数语言没有维基。"
        "第四，但它不是单向的漏斗——最濒危的那一档里，仍然有两门语言在数字空间里活着。")

# ============================================================ 24 两个例子
s = slide(24, "四、结论与展望")
kicker(s, "两个小例子 · 比结论更有说服力")
headline(s, "康沃尔语，和那个 10,270%", 0.92, 30)

rect(s, 0.72, 1.95, 5.85, 3.3, SUBTLE, radius=0.12)
tb(s, 1.02, 2.12, 5.3, 0.45, "例一 · 口语已消亡，数字却在涨", 13, ACCENT, True)
tb(s, 1.02, 2.62, 5.3, 0.5, "康沃尔语 Cornish", 19, INK, True)
for i, line in enumerate([
    "最后一位母语者 1777 年去世 —— 作为口语，它已经消失了两百多年。",
    "但它的维基月阅读量从 10.3 万涨到 215 万，是原来的 21 倍（+2003%）。",
    "马恩岛语同理：最后一位母语者 1974 年，数字关注度同样在涨。",
    "这说明「数字缺席」不是宿命 —— 数字空间可以替一门语言续命。",
]):
    tb(s, 1.02, 3.15 + i * 0.52, 5.3, 0.5, "· " + line, 11.5, INK2, spacing=1.45)

rect(s, 6.9, 1.95, 5.7, 3.3, SUBTLE, radius=0.12)
tb(s, 7.2, 2.12, 5.1, 0.45, "例二 · 增长率本身也会骗人", 13, ACCENT, True)
tb(s, 7.2, 2.62, 5.1, 0.5, "塞德克语 Seediq: +10,270%", 18, INK, True)
for i, line in enumerate([
    "这个数字不是「涨了一万倍」的意思——它的基线只有个位数。",
    "任何一个月的小波动，都能把比值放大到荒谬的量级。",
    "所以我加了「去除记录数据过少的语言」开关，默认把这批剔除。",
    "这也是我下一步想换成趋势检验（而非首尾比值）的原因。",
]):
    tb(s, 7.2, 3.15 + i * 0.52, 5.1, 0.5, "· " + line, 11.5, INK2, spacing=1.45)

tb(s, 0.72, 5.55, 11.9, 0.5,
   "还有一个只有我知道的小细节：WALS 码 deu 在这份数据里指的是 Deuri（德乌里语），不是德语。"
   "三套编号体系撞码，是清洗阶段最容易出错的地方。", 11.5, MUTED, spacing=1.5)
note(s, "讲两个小例子。康沃尔语，最后一位母语者 1777 年去世，口语层面它已经消失两百多年，"
        "但它的维基月阅读量从十万涨到两百一十五万，是原来的二十一倍。"
        "马恩岛语一样，最后一位母语者 1974 年。所以数字缺席不是宿命。"
        "第二个例子反过来看：塞德克语涨了百分之一万零二百七十——"
        "这不是涨了一万倍，而是它的基线只有个位数，任何小波动都会被放大。"
        "所以我做了「去除记录数据过少的语言」这个开关。"
        "顺便说个只有我知道的坑：WALS 码 d-e-u 在这份数据里是德乌里语，不是德语。")

# ============================================================ 25 不足与展望
s = slide(25, "四、结论与展望")
kicker(s, "不足 · 和下一步")
headline(s, "三点不足，三条下一步", 0.92, 30)
items = [
    ("覆盖面", "只覆盖 WALS 的 2,662 门有语法记录的变体，不能外推到七千种。",
     "接入 Glottolog 全量 + 濒危语言名录，把覆盖推到七千门量级。"),
    ("单平台", "维基百科只是一个平台，且受新闻事件与病毒式传播影响。",
     "扩到 YouTube / X 的语种标签，做多平台对照，看结论是否稳。"),
    ("端点敏感", "增长率用首尾比值，对基线过小的语言失真（见上页 Seediq）。",
     "改用 Mann–Kendall 趋势检验 + Sen 斜率，让「在涨」有显著性而非比值。"),
]
for i, (h, d, nxt) in enumerate(items):
    y = 1.98 + i * 1.55
    tb(s, 0.72, y, 1.5, 0.42, h, 13.5, ACCENT, True)
    tb(s, 2.1, y - 0.02, 5.2, 0.9, d, 12, INK2, spacing=1.5)
    tb(s, 7.7, y - 0.02, 4.9, 0.9, "→ " + nxt, 12, INK, spacing=1.5)
    if i < 2:
        rect(s, 0.72, y + 1.34, 11.9, 0.008, RGBColor(0xE8, 0xE2, 0xD6))
tb(s, 0.72, 6.72, 11.9, 0.4,
   "这三条都不是推倒重来：数据契约不变，换掉计算与数据源即可。", 11.5, MUTED)
note(s, "不足有三点，我都主动说。第一覆盖面，只有 WALS 收录的两千六百多门，"
        "不能外推到七千种。第二，维基只是一个平台。第三，增长率用首尾比值，"
        "对基线太小的语言会失真。对应的下一步：接全量 Glottolog、扩多平台、"
        "把比值换成 Mann-Kendall 趋势检验。这三条都不用推倒重来，"
        "因为数据契约没变，换掉计算和数据源就行。")

# ============================================================ 26 参考文献
s = slide(26, "四、结论与展望")
kicker(s, "参考文献")
headline(s, "数据、方法与设计依据", 0.92, 28)
refs = [
    "[1] Dryer M S, Haspelmath M (eds.). The World Atlas of Language Structures Online. 2013.",
    "[2] Hammarström H, Forkel R, Haspelmath M, Bank S. Glottolog 5.0. 2024.",
    "[3] UNESCO. Language Vitality and Endangerment. 2003.",
    "[4] Wikimedia Foundation. Wikimedia REST API: Pageviews. 2026.",
    "[5] Wikidata Query Service. Properties P1999, P279. 2026.",
    "[6] Joshi P, Santy S, Budhiraja A, et al. The State and Fate of Linguistic Diversity. 2020.",
    "[7] Ronen S, Gonçalves B, Hu K Z, et al. Links that speak. PNAS, 2014.",
    "[8] Graham M, Hogan B, Straumann R K, Medhat A. Uneven geographies of Wikipedia. 2014.",
    "[9] 陈为, 沈则潜, 陶煜波. 数据可视化. 电子工业出版社, 2013.",
]
for i, r in enumerate(refs):
    tb(s, 0.72, 1.92 + i * 0.52, 11.9, 0.45, r, 10.5, INK2, name=MONO)
note(s, "参考文献。数据来自 WALS、Glottolog、UNESCO、维基媒体和 Wikidata，"
        "方法与设计参考了 Joshi 等人的语言多样性研究、Ronen 等人的网络语言学工作，"
        "以及陈为老师的数据可视化教材。")

'''

s = s[:start] + NEW + s[end:]

# 页脚统一
s = s.replace('"四、规律与结论")', '"四、结论与展望")')

io.open(P, "w", encoding="utf-8").write(s)
print("  ok   第四部分已重写为 4 页（规律 / 例子 / 不足与展望 / 参考文献）")
