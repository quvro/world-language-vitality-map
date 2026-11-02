import io
from docx import Document
d = Document(r"paper/世界语言赛博活力图谱_课程论文.docx")
out = []
for p in d.paragraphs:
    t = p.text.strip()
    if t:
        out.append(f"[{p.style.name}] {t}")
for i, tb in enumerate(d.tables):
    out.append(f"===== TABLE {i} =====")
    for row in tb.rows:
        out.append(" | ".join(c.text.strip() for c in row.cells))
io.open("paper/_docx_text.txt","w",encoding="utf-8").write("\n".join(out))
print("paras:", len(d.paragraphs), "chars:", sum(len(x) for x in out))
