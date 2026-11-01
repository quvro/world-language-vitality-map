"""修选项卡被挤成两行：标签不换行 + 控件文案收短。"""

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

# 1) 标签禁止折行（之前 1500px 下被挤成「地 图」两行）
sub(A,
    """.tabs button {
  border: 0; background: transparent; cursor: pointer; font-family: inherit;
  padding: 6px 14px; border-radius: var(--radius-pill);""",
    """.tabs button {
  border: 0; background: transparent; cursor: pointer; font-family: inherit;
  /* 不换行：控件移进来后横向变紧，1500px 下曾把「地图」挤成两行 */
  white-space: nowrap;
  padding: 6px 13px; border-radius: var(--radius-pill);""",
    "标签不换行")

# 2) 极窄时允许整行横向滚动，而不是把内容压变形
sub(A,
    """.tabs .tabs-right { margin-left: auto; display: flex; align-items: center; }""",
    """.tabs .tabs-right { margin-left: auto; display: flex; align-items: center; flex: none; }
/* 兜底：窗口极窄时让标签行横向滚动，而不是把字压成两行 */
.tabs { overflow-x: auto; scrollbar-width: none; }
.tabs::-webkit-scrollbar { display: none; }""",
    "窄屏兜底")

# 3) 控件文案收短，把宽度还给标签
M = "web/src/components/MapControls.vue"
sub(M, "    byMacro: '按语区', byTrend: '按趋势',", "    byMacro: '语区', byTrend: '趋势',", "控件文案 1")
sub(M, "    sizeRel: '相对自身峰值', sizeAbs: '跨语言比较',",
    "    sizeRel: '自身峰值', sizeAbs: '跨语言',", "控件文案 2")
sub(M, "    vitalityLayer: '活力层',", "    vitalityLayer: '活力',", "控件文案 3")
sub(M, "    onlySelected: '只看选中',", "    onlySelected: '选中',", "控件文案 4")
sub(M, "    byMacro: 'By area', byTrend: 'By trend',", "    byMacro: 'Area', byTrend: 'Trend',", "EN 1")
sub(M, "    sizeRel: 'vs own peak', sizeAbs: 'across langs',",
    "    sizeRel: 'own peak', sizeAbs: 'across',", "EN 2")
sub(M, "    vitalityLayer: 'Vitality',", "    vitalityLayer: 'Vitality',", "EN 3")
sub(M, "    onlySelected: 'Selected only',", "    onlySelected: 'Selected',", "EN 4")
