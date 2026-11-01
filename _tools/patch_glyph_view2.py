"""修掉 WorldMap 里剩下的 mapDensity 引用。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/components/WorldMap.vue"
s = io.open(P, encoding="utf-8").read()
n = 0
for old, new in [
    ("// 先改 geo（一次 setOption），再改 mapDensity ——",
     "// 先改 geo（一次 setOption），再改 mapMode ——"),
    ("store.mapDensity = false", "store.mapMode = 'dots'"),
    ("（store.mapDensity）", "（store.mapMode）"),
]:
    if old in s:
        c = s.count(old)
        s = s.replace(old, new)
        n += c
        print(f"  {old[:34]!r} × {c}")
io.open(P, "w", encoding="utf-8").write(s)
print(f"  共替换 {n} 处")
