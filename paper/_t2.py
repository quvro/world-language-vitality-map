import io
from pptx import Presentation
p = Presentation(r"paper/世界语言赛博活力图谱_答辩PPT.pptx")
out=[]
for i, s in enumerate(p.slides, 1):
    if i not in (11,12,13,14,16,17,18,19,20): continue
    out.append(f"===== {i:02d} =====")
    for sh in s.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            out.append(sh.text_frame.text.strip())
io.open("paper/_t2.txt","w",encoding="utf-8").write("\n".join(out))
print("ok")
