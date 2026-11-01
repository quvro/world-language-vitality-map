"""用明确的包裹类替代 :first-child / :last-child。

病根：空状态下右栏只有一个子元素，它同时命中 :first-child 与 :last-child。
两条规则优先级相同、:last-child 在后 → max-height:46% 生效 → 卡片正好只剩一半。
这就是用户反复说"还是一样"的原因：我前两次都在改 flex 值，而覆盖来自选择器。

改成包裹 div + 类名，两者互不干扰。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

A = "web/src/App.vue"
s = io.open(A, encoding="utf-8").read()

# 1) 模板：加包裹类
OLD_T = """        <div class="right-stack">
          <LanguageCard />
          <HealthBars />
        </div>"""
NEW_T = """        <div class="right-stack">
          <div class="rc-card"><LanguageCard /></div>
          <div class="rc-health"><HealthBars /></div>
        </div>"""
if OLD_T in s:
    s = s.replace(OLD_T, NEW_T, 1)
    print("  ok   模板已加包裹类")
else:
    print("  MISS 模板")

# 2) 样式：整段替换掉位置选择器版本
START = "/* 右栏第一张卡片与把手拼接"
END = ".right-stack > :last-child {\n  flex: 0 1 auto;\n  min-height: 0;\n  max-height: 46%;\n  overflow-y: auto;\n}"
i = s.find(START)
j = s.find(END)
if i >= 0 and j >= 0:
    NEW_CSS = """/* 右栏布局。
   踩过的坑：原来用 :first-child / :last-child，结果空状态下只有一个子元素，
   它同时命中两条规则、后者覆盖前者（max-height:46%），卡片正好只剩一半。
   改成显式类名，互不干扰。 */
.rc-card {
  flex: 1 1 auto;          /* 占满可用高度 */
  min-height: 0;           /* flex 子项不加这条不会真正收缩 */
  overflow-y: auto;
  /* 与左侧把手拼接 */
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}
.rc-health {
  flex: 0 1 auto;
  min-height: 0;
  max-height: 46%;
  overflow-y: auto;
}
.rc-card > :first-child {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}"""
    s = s[:i] + NEW_CSS + s[j + len(END):]
    io.open(A, "w", encoding="utf-8").write(s)
    print("  ok   样式已改为显式类名")
else:
    print(f"  MISS 样式区间 i={i} j={j}")
    io.open(A, "w", encoding="utf-8").write(s)
