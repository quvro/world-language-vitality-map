import sys, io
from pptx import Presentation
p = Presentation(r"paper/世界语言赛博活力图谱_答辩PPT.pptx")
out = []
for i, s in enumerate(p.slides, 1):
    out.append(f"===== SLIDE {i:02d} =====")
    for sh in s.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            out.append("[TEXT] " + sh.text_frame.text.strip())
            for para in sh.text_frame.paragraphs:
                for r in para.runs:
                    pass
        if sh.has_table:
            out.append("[TABLE]")
            for row in sh.table.rows:
                out.append(" | ".join(c.text.strip() for c in row.cells))
    if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip():
        out.append("[NOTES] " + s.notes_slide.notes_text_frame.text.strip())
io.open("paper/_slides_text.txt","w",encoding="utf-8").write("\n".join(out))
print("ok", len(out))
