"""从 PPT 备注导出可打印讲稿，并按时长比例分配每一页的秒数。

本次重写的原因：原来 TITLES / TIPS 是**硬编码的 14 条**，用 zip 与备注配对。
PPT 从 14 页扩到 21 页、再到 24 页之后，zip 直接按短的截断 ——
讲稿只剩前 14 页，后半场完全没有稿子，页标题也停在旧版。
现在标题改为**从幻灯片自动提取**（取字号最大的一行），PPT 再加页也不用改这里。
TIPS 变成按页号取的字典，缺失时给中性提示，不会再让整份稿子错位。
"""

import re
import sys

from pptx import Presentation

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PPTX = "paper/世界语言赛博活力图谱_答辩PPT_新.pptx"
OUT = "paper/答辩讲稿.md"
TOTAL_SEC = 600

# 按页号给提示。注意：在中间插入新页会让后面的页码整体后移，
# 所以这里只写内容稳定靠前的页 + 本次新增的 17–19 页 + 末页。
TIPS = {
    1: "停 2 秒再开口，让观众看清题目。",
    2: "指一下三个大数字，再回到「不存在」这三个字。",
    3: "三张卡片从左到右点一遍，最后落到「双重缺席」。",
    4: "语速加快，四个问题一口气念完，不要停顿解释。",
    5: "表格不求逐行念，只强调最后一句「口径互不相干」。",
    6: "这张图不用细讲，一句话带过，重点在「换数据不用改视图」。",
    7: "用鼠标沿六个视图划一圈，只念每个视图的关键词。",
    8: "这是全场最重要的停顿点：先让观众看到矩阵，再解释「横带」。",
    9: "点一下地图上那块橙色区域，说明 146 门里只有 11 门有维基。",
    10: "四根条一起看——都往上走。这是一句话就能说服人的证据。",
    11: "快速过，不要念细节；重点是「文案数字实时计算」。",
    12: "放慢。每一行念完停 1 秒，第四行是全场的反转点。",
    13: "局限要主动说，显得诚实；展望一句话即可。",
    17: "先把五个部件按顺序念一遍，再当场关掉一个给评委看。",
    18: "强调「只在有数据的语言里算百分位」——这里最容易讲错。",
    19: "说清三段职责，重点落在「检索留在前端，数字不会错」。",
    24: "鞠躬，等提问。",
}
DEFAULT_TIP = "看图讲解，不要念稿；这一页控制在 20 秒内。"


def slide_title(sl) -> str:
    """取字号最大的一行文字作为页标题（封面与分隔页也能取到）。"""
    # 优先取**含中文**且不太短的文本：
    # 幻灯片里字号最大的往往是那个大数字（10.0%、2,662、01），
    # 直接按字号取会把页标题取成数字，读起来毫无意义。
    cand = []
    for sh in sl.shapes:
        if not sh.has_text_frame:
            continue
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                t = r.text.strip()
                if not (2 <= len(t) <= 34):
                    continue
                size = r.font.size.pt if r.font.size else 0.0
                cand.append((size, t))
    if not cand:
        return "（过渡页）"
    cjk = [c for c in cand if len(c[1]) >= 5 and re.search(r'[\u4e00-\u9fff]', c[1])]
    pool = cjk or cand
    return max(pool, key=lambda c: c[0])[1]


prs = Presentation(PPTX)
notes, titles = [], []
for sl in prs.slides:
    txt = ""
    if sl.has_notes_slide:
        txt = sl.notes_slide.notes_text_frame.text.strip()
    notes.append(txt)
    titles.append(slide_title(sl))

total_chars = sum(len(n) for n in notes)
mins = total_chars / 190.0  # 中文演讲的舒适语速约 190 字/分钟

lines = [
    "# 答辩讲稿 · 世界语言赛博活力图谱",
    "",
    f"> 共 {len(notes)} 页，讲稿 {total_chars} 字，按 **10 分钟**（600 秒）分配。",
    f"> 以 190 字/分钟的舒适语速计算约 **{mins:.1f} 分钟**。"
    + ("　⚠️ **已超过 10 分钟限制，需要删减。**" if mins > 10.5 else ""),
    "",
    "> 页标题由脚本从幻灯片自动提取，与 PPT 保持一致，不再手工维护。",
    "",
    "---",
    "",
]
acc = 0
for i, (n, title) in enumerate(zip(notes, titles), start=1):
    sec = round(TOTAL_SEC * len(n) / total_chars) if total_chars else 0
    acc += sec
    lines += [
        f"## 第 {i:02d} 页 · {title}",
        "",
        f"⏱ **约 {sec} 秒**　（累计 {acc / 60:.1f} 分钟）",
        "",
        n or "（本页无备注）",
        "",
        f"> 💡 {TIPS.get(i, DEFAULT_TIP)}",
        "",
        "---",
        "",
    ]

lines += [
    "## 可能被问到的问题（准备用）",
    "",
    "**Q：为什么用浏览量而不是文章数？**",
    "A：文章数可以被机器人灌水。Kornai 在 2013 年的论文里就警告过「波将金维基」——"
    "瓦洛夫语维基的文章数排第 37，但几乎全是机器生成的地理条目。浏览量不能这样造假。",
    "",
    "**Q：维基百科能代表整个互联网吗？**",
    "A：不能，这是明确的局限。但我用四套互不相干的记录口径做了交叉验证，"
    "方向一致，说明结论不是维基这一个数据源造成的。",
    "",
    "**Q：为什么只有 2,662 门语言，不是七千种？**",
    "A：因为 WALS 只收录了 2,662 门有语法记录的变体。这是个取舍："
    "用 WALS 换来了 192 个语法特征，代价是覆盖不到全部语言。"
    "而这个取舍本身就是结论的一部分——没有语法记录的语言，恰恰也最缺数字记录。",
    "",
    "**Q：创新点里哪个最有价值？**",
    "A：四套口径交叉验证。前两个（数据缺口可视化、语系星群）是表现手法上的创新，"
    "而这个是方法论上的——它让结论从「我观察到」变成「四套数据都这么说」。",
    "",
    "**Q：复合字形五个部件会不会太复杂、观众看不懂？**",
    "A：会，所以做了通道开关：默认全开，可以逐个关掉；关掉后部件变灰而不是消失，"
    "这样「这一层信息有多少」是看得见的。现场我会关掉一个演示，视觉变化很明显。",
    "",
    "**Q：大模型会不会编数字？**",
    "A：不会，因为检索不在模型里。所有统计都在前端从当前筛选结果算出来，"
    "模型只拿到算好的证据包去措辞。而且没有密钥时用本地模板合成，链路一样跑得通。",
    "",
    "**Q：数据是你自己采集的吗？**",
    "A：是。五个来源全部通过公开 API 或可复现脚本抓取，共 157,736 行、9 张表；"
    "7 个采集脚本都是幂等的，重跑结果一致。",
    "",
]

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print(f"  已生成 {OUT}")
print(f"  页数 {len(notes)}，讲稿 {total_chars} 字，估计 {mins:.1f} 分钟")
missing = [i for i, n in enumerate(notes, 1) if not n]
print(f"  无备注的页: {missing if missing else '无'}")
