"""修章节页备注贴错页：note(s, ...) 里的 s 还指向上一个内容页。

修法：把 divider(8, ...) 改成 s = divider(8, ...)，让 s 指向章节页本身。
"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

pat = re.compile(r'^divider\((\d+), (.*)\)\nnote\(s, ', re.M)
s2, n = pat.subn(lambda m: f's = divider({m.group(1)}, {m.group(2)})\nnote(s, ', s)
io.open(P, "w", encoding="utf-8").write(s2)
print(f"  改写 {n} 处 divider 为 s = divider(...)")

# 检查：每个 note(s, ...) 前面最近的一行是否是 s = ...
lines = s2.splitlines()
bad = []
for i, ln in enumerate(lines):
    if ln.startswith("note(s,") or ln.startswith("note(s, "):
        prev = lines[i - 1] if i else ""
        if not (prev.startswith("s = slide(") or prev.startswith("s = divider(")):
            bad.append((i + 1, prev[:52]))
print("  可疑行：", bad if bad else "无")
