"""检查生成的论文：图片数、标题层级、字数、表格、是否有残留占位符。"""
import sys

from docx import Document

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = "paper/世界语言赛博活力图谱_课程论文.docx"
doc = Document(p)

paras = doc.paragraphs
chars = sum(len(x.text) for x in paras)
imgs = len(doc.inline_shapes)
tables = len(doc.tables)

print(f"段落 {len(paras)}，字符 {chars}，图片 {imgs}，表格 {tables}")
print("=" * 70)
for i, x in enumerate(paras):
    if not x.text.strip():
        continue
    style = x.style.name
    tag = "H1" if style == "Heading 1" else ("H1s" if style == "Heading 1" else "  ")
    print(f"[{i:3d}] {tag} {x.text[:78]}")

print("=" * 70)
print("表格：")
for ti, t in enumerate(doc.tables):
    print(f"  表 {ti}: {len(t.rows)} 行 x {len(t.columns)} 列  首行="
          + " | ".join(c.text.strip()[:18] for c in t.rows[0].cells))

# 残留占位符检查
bad = []
for x in paras:
    t = x.text
    if "xxxx" in t or "####" in t or "【重点写】" in t or "此图是图例" in t:
        bad.append(t[:60])
print("\n残留占位符：", bad if bad else "无")

# 图片是否都是真实文件
print("\n图片宽度（cm）：")
for s in doc.inline_shapes:
    print(f"  {s.width.cm:.1f} x {s.height.cm:.1f}")
