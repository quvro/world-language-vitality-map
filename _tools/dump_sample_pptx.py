"""拆解样例 PPT：画布比例、配色、字体、每页的版式与元素构成。"""

import sys
from collections import Counter

from pptx import Presentation
from pptx.util import Emu

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = r"C:\Users\sunyn\Desktop\1\04序号_学号_姓名_xxx研讨报告（每人一份）基于Hadoop的城市公共交通大数据时空分析.pptx"
prs = Presentation(p)

print(f"画布：{prs.slide_width/914400:.2f} x {prs.slide_height/914400:.2f} 英寸"
      f"（{prs.slide_width/prs.slide_height:.3f}）")
print(f"页数：{len(prs.slides)}")
print("=" * 76)

colors = Counter()
fonts = Counter()
sizes = Counter()

for i, s in enumerate(prs.slides, 1):
    kinds = Counter()
    texts = []
    for sh in s.shapes:
        kinds[sh.shape_type] += 1
        if sh.has_text_frame:
            t = sh.text_frame.text.strip().replace("\n", " / ")
            if t:
                texts.append(t[:60])
            for para in sh.text_frame.paragraphs:
                for r in para.runs:
                    if r.font.name:
                        fonts[r.font.name] += 1
                    if r.font.size:
                        sizes[r.font.size.pt] += 1
                    try:
                        if r.font.color and r.font.color.rgb:
                            colors[str(r.font.color.rgb)] += 1
                    except Exception:
                        pass
        if sh.shape_type == 13:  # PICTURE
            texts.append(f"[图片 {sh.width/914400:.1f}x{sh.height/914400:.1f}in]")
    print(f"\n— 第 {i} 页 — 形状 {len(s.shapes)}：{dict(kinds)}")
    for t in texts[:7]:
        print(f"    · {t}")
    if len(texts) > 7:
        print(f"    …另有 {len(texts)-7} 段文字")

print("\n" + "=" * 76)
print("字体 Top8：", fonts.most_common(8))
print("字号 Top8：", sizes.most_common(8))
print("文字颜色 Top8：", colors.most_common(8))

# 背景
try:
    bg = prs.slides[0].background.fill
    print("首页背景 fill type:", bg.type)
except Exception as e:
    print("背景读取失败:", e)
