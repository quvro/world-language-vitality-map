"""修章节过渡页：大数字压住标题、强调线穿过数字、页脚显示成编号。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

old_start = s.index("def divider(no, zh, en, desc, nt=\"\"):")
old_end = s.index("divider(3,")

new_fn = '''def divider(no, zh, en, desc, nt=""):
    """章节过渡页。

    排版是踩出来的：最初把 110pt 的大号数字放在 y=2.35、标题放在 3.95，
    结果数字的下沿一直压到标题上，强调线又正好穿过数字中间。
    现在数字缩到 76pt 并整体上移，强调线放在数字与标题之间的空白里。
    页脚也改成题名 —— 原来传的是 "02"，会和右下角的页码混淆。
    """
    s = slide(no, "世界语言赛博活力图谱")
    tb(s, 0.72, 1.78, 4.2, 1.15, f"{int(en):02d}", 76,
       RGBColor(0xDF, 0xD4, 0xC2), True, name=MONO)
    rect(s, 0.72, 3.2, 0.95, 0.05, ACCENT)
    tb(s, 0.72, 3.45, 9.0, 0.65, zh, 33, INK, True)
    tb(s, 0.72, 4.18, 9.6, 0.6, desc, 15, INK2)
    if nt:
        note(s, nt)
    return s


'''

s = s[:old_start] + new_fn + s[old_end:]
io.open(P, "w", encoding="utf-8").write(s)
print("  divider() 已重排")
