"""修排版：胶囊标签宽度不足导致换行；正文宽度不够导致句号掉行。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt.py"
s = io.open(P, encoding="utf-8").read()

PAIRS = [
    # 1) 胶囊宽度按中文字数算准，并禁止换行
    ('    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t),\n'
     '                             Inches(0.12 + 0.115 * len(text)), Inches(0.3))',
     '    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t),\n'
     '                             Inches(0.42 + 0.165 * len(text)), Inches(0.32))'),
    ('    p = box.text_frame.paragraphs[0]\n'
     '    p.alignment = PP_ALIGN.CENTER',
     '    box.text_frame.word_wrap = False\n'
     '    p = box.text_frame.paragraphs[0]\n'
     '    p.alignment = PP_ALIGN.CENTER'),
    # 2) 第 2 页正文放宽，避免标点掉行
    ('tb(s, 0.72, 2.0, 7.4, 1.2,\n'
     '   "全球约 7,000 种语言，能在维基百科上拥有独立入口的只有 267 种，"\n'
     '   "占本数据集 2,662 门语言的 10.0%；其余 2,395 门在互联网上没有自己的入口。",\n'
     '   16, INK2, spacing=1.5)',
     'tb(s, 0.72, 1.98, 11.5, 1.15,\n'
     '   "全球约 7,000 种语言，能在维基百科上拥有独立入口的只有 267 种，"\n'
     '   "占本数据集 2,662 门语言的 10.0%；其余 2,395 门在互联网上没有自己的入口。",\n'
     '   17, INK2, spacing=1.5)'),
]

hit = 0
for old, new in PAIRS:
    if old in s:
        s = s.replace(old, new, 1)
        hit += 1
    else:
        print("  未匹配：", old[:52].replace("\n", "\\n"))

io.open(P, "w", encoding="utf-8").write(s)
print(f"  替换 {hit}/{len(PAIRS)} 处")
