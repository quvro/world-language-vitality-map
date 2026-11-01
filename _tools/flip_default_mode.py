"""把 store 里 mapMode 的默认值改成指定值（双向都支持）。"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/stores/dataset.ts"
mode = sys.argv[1] if len(sys.argv) > 1 else "density"
s = io.open(P, encoding="utf-8").read()
s2, n = re.subn(r"(?m)^(\s+)mapMode: '(?:density|dots|glyph)',$",
                lambda m: f"{m.group(1)}mapMode: '{mode}',", s, count=1)
if n:
    io.open(P, "w", encoding="utf-8").write(s2)
    print(f"  mapMode 默认值 → {mode}")
else:
    print("  !! 没匹配到默认值行")
