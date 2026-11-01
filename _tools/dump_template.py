"""把模板 .docx 的结构完整打印出来，用于照着写论文。"""
import sys
from docx import Document
from docx.shared import Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

doc = Document("docs/_template.docx")
print(f"段落 {len(doc.paragraphs)}，表格 {len(doc.tables)}，节 {len(doc.sections)}")
sec = doc.sections[0]
print(f"页面 {sec.page_width.cm:.1f} x {sec.page_height.cm:.1f} cm，"
      f"页边距 上{sec.top_margin.cm:.1f} 下{sec.bottom_margin.cm:.1f} "
      f"左{sec.left_margin.cm:.1f} 右{sec.right_margin.cm:.1f}")
print("=" * 78)

for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    style = p.style.name
    # 字号与字体
    size = None
    font = None
    bold = None
    ea = None
    for r in p.runs:
        if r.font.size:
            size = r.font.size.pt
        if r.font.name:
            font = r.font.name
        if r.font.bold is not None:
            bold = r.font.bold
        rpr = r._element.rPr
        if rpr is not None and rpr.rFonts is not None:
            ea = rpr.rFonts.get(
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia")
        break
    align = p.alignment
    mark = ""
    if not text:
        mark = "  [空行]"
    print(f"[{i:3d}] <{style}> {text[:120]!r}{mark}")
    if text and (size or font or ea or bold is not None or align is not None):
        print(f"       字号={size} 字体={font} 中文字体={ea} 粗体={bold} 对齐={align}")

print("=" * 78)
for ti, t in enumerate(doc.tables):
    print(f"表格 {ti}: {len(t.rows)} 行 x {len(t.columns)} 列")
    for ri, row in enumerate(t.rows):
        cells = [c.text.strip().replace("\n", " / ")[:40] for c in row.cells]
        print(f"  [{ri}] " + " | ".join(cells))
