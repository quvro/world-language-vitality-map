"""把 divider 之后单独 note() 的写法，统一改成传 nt= 进 divider()。"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

pat = re.compile(
    r'(divider\(\s*\d+,\s*"[^"]*",\s*"[^"]*",\s*"[^"]*")\s*\)\s*\n'
    r'note\(prs\.slides\[-1\],\s*"([^"]*)"\)'
)
s2, n = pat.subn(lambda m: f'{m.group(1)},\n        "{m.group(2)}")', s)
io.open(P, "w", encoding="utf-8").write(s2)
print(f"  改写 {n} 处")

left = len(re.findall(r"prs\.slides\[-1\]", s2))
print(f"  仍残留 prs.slides[-1]：{left} 处")
