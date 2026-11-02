import io
from pptx import Presentation
p = Presentation(r"paper/世界语言赛博活力图谱_答辩PPT.pptx")
lines = []
for i, s in enumerate(p.slides, 1):
    t = []
    for sh in s.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            t.append(sh.text_frame.text.strip().split("\n")[0])
    lines.append(f"{i:02d} | " + " || ".join(t[:4]))
io.open("paper/_titles.txt","w",encoding="utf-8").write("\n".join(lines))
print(len(p.slides))
