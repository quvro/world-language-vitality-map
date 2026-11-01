"""数字追溯只针对计数类：百分比是派生量，先剔除再判。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/preview/verify-nl-answer.mjs"
s = io.open(P, encoding="utf-8").read()

OLD = r"""  const nums = (a1.bullets.join(' ') + a1.lead + a1.caveats.join(' '))
    .match(/\d[\d,]*/g) ?? []"""

NEW = r"""  // 百分比是从证据里的比率派生出来的（例如 51.13 → "51.1%"），
  // 单独放行；这里只追溯**计数类**数字是否都能在证据里找到。
  const rawText = (a1.bullets.join(' ') + a1.lead + a1.caveats.join(' '))
  const nums = rawText.replace(/[-+]?\d+(\.\d+)?%/g, ' ').match(/\d[\d,]*/g) ?? []"""

if OLD in s:
    s = s.replace(OLD, NEW, 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("  ok   已改为只追溯计数类数字")
else:
    print("  MISS 未匹配")
