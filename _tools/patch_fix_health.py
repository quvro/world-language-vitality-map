"""收尾两项：体检单始终可见；字形面板默认收起。

体检单"看不到"的真实原因：右栏是纵向 flex，LanguageCard 把高度占满，
HealthBars 被挤到滚动区之外 —— 高度稍矮的窗口就完全看不见，
而且右栏没有可见滚动条提示，用户不会想到去滚。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def sub(path, old, new, tag):
    s = io.open(path, encoding="utf-8").read()
    if old in s:
        io.open(path, "w", encoding="utf-8").write(s.replace(old, new, 1))
        print(f"  ok   {tag}")
    else:
        print(f"  MISS {tag}")


A = "web/src/App.vue"

# 1) 右栏：卡片自身可滚动，体检单固定在下、始终可见
sub(A,
    """/* 右栏第一张卡片与把手拼接：左侧圆角归零，看起来是同一个容器 */
.right-stack > :first-child {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}""",
    """/* 右栏第一张卡片与把手拼接：左侧圆角归零，看起来是同一个容器 */
.right-stack > :first-child {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}
/* 关键：让详情卡自己滚动、并把高度让出来，体检单永远留在可视区。
   之前卡片把高度占满，体检单被挤到滚动区外，窗口矮一点就"完全看不到"。 */
.right-stack > :first-child {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
}
.right-stack > :last-child { flex: none; }""",
    "体检单始终可见")

# 2) 字形面板默认收起（用户反馈它挡地图）
sub("web/src/stores/dataset.ts",
    "    glyphPanelOpen: true,",
    "    // 默认收起：展开时会盖住南美洲一块。收起后仍显示「5/5」，信息不丢\n"
    "    glyphPanelOpen: false,",
    "面板默认收起")
