"""把「语言体检单」挂到右栏 LanguageCard 下面。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/App.vue"
s = io.open(P, encoding="utf-8").read()

if "HealthBars" in s:
    print("  已挂载，跳过")
    raise SystemExit(0)

s = s.replace(
    "import AnswerPanel from '@/components/AnswerPanel.vue'",
    "import AnswerPanel from '@/components/AnswerPanel.vue'\n"
    "import HealthBars from '@/components/HealthBars.vue'",
    1,
)

# 找一个「LanguageCard 之后」的位置插入
i = s.find("<LanguageCard")
if i < 0:
    print("  MISS 找不到 LanguageCard")
    raise SystemExit(1)
end = s.find("/>", i) + 2
s = s[:end] + "\n        <HealthBars />" + s[end:]

io.open(P, "w", encoding="utf-8").write(s)
print("  已挂载 HealthBars")
