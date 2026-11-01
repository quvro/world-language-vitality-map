"""把右栏的「卡片 + 体检单」包成纵向容器。

原因：`.col-right` 是 `display:flex; align-items:stretch`（横向），
我直接把 <HealthBars /> 插在 <LanguageCard /> 后面，它就成了并排的第二个"列"，
被压成零宽 —— 所以完全看不见。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/App.vue"
s = io.open(P, encoding="utf-8").read()

OLD = "        <LanguageCard />\n        <HealthBars />"
NEW = (
    "        <div class=\"right-stack\">\n"
    "          <LanguageCard />\n"
    "          <HealthBars />\n"
    "        </div>"
)

if OLD in s:
    s = s.replace(OLD, NEW, 1)
    print("  ok   已包成 right-stack")
elif '<div class="right-stack">' in s:
    print("  已包过，跳过")
else:
    # 退一步：分别替换两个标签
    a = s.find("<LanguageCard")
    b = s.find("<HealthBars")
    print("  MISS 精确片段，改用逐标签处理:", a, b)

# 样式：右栏内容纵向排列，超出可滚动
if ".right-stack {" not in s:
    s = s.replace(
        ".col-left, .col-right { min-height: 0; }",
        """.col-left, .col-right { min-height: 0; }
/* 右栏里的「卡片 + 体检单」纵向排列。col-right 本身是横向 flex（把手 + 内容），
   所以内容必须再包一层纵向容器，否则体检单会被当成第二个"列"压成零宽 */
.right-stack {
  flex: 1; min-width: 0; min-height: 0;
  display: flex; flex-direction: column; gap: var(--sp-2);
  overflow-y: auto;
}""",
        1,
    )
    print("  ok   已加 .right-stack 样式")

io.open(P, "w", encoding="utf-8").write(s)
