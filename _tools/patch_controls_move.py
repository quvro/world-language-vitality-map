"""把地图控件挪到选项卡行；把手与右栏连成一体；恢复选项卡高度。"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(p):
    return io.open(p, encoding="utf-8").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def sub(path, old, new, tag):
    s = load(path)
    if old in s:
        save(path, s.replace(old, new, 1))
        print(f"  ok   {tag}")
    else:
        print(f"  MISS {tag}")


A = "web/src/App.vue"

# 1) 选项卡行：左边标签、右边控件；并给回一点上下内边距（之前被我压扁了）
sub(A,
    ".tabs { display: flex; gap: var(--sp-1); }",
    """.tabs {
  display: flex; align-items: center; gap: var(--sp-1);
  /* 上下留 5px：上一版为了让标签贴住卡片把间隙全去掉了，
     结果整行被压扁，看着像"选项卡变短了"。这里把高度补回来。 */
  padding: 5px 0 4px;
}
.tabs .tabs-right { margin-left: auto; display: flex; align-items: center; }""",
    "选项卡行布局")

# 2) 把控件挂到选项卡行右侧
OLD_NAV = """        <nav class="tabs">
          <button
            v-for="v in VIEWS"
            :key="v.id"
            :class="{ on: store.activeView === v.id }"
            @click="store.activeView = v.id"
          >{{ v.label }}</button>
        </nav>"""
NEW_NAV = """        <nav class="tabs">
          <button
            v-for="v in VIEWS"
            :key="v.id"
            :class="{ on: store.activeView === v.id }"
            @click="store.activeView = v.id"
          >{{ v.label }}</button>
          <!-- 地图那一排控件附着在选项卡行上（只在看地图时出现） -->
          <span class="tabs-right">
            <MapControls v-if="store.activeView === 'map'" />
          </span>
        </nav>"""
sub(A, OLD_NAV, NEW_NAV, "控件挂到选项卡行")

# 3) 引入组件
sub(A,
    "import HealthBars from '@/components/HealthBars.vue'",
    "import HealthBars from '@/components/HealthBars.vue'\n"
    "import MapControls from '@/components/MapControls.vue'",
    "引入 MapControls")

# 4) 把手与右栏连成一体：去掉间隙，把手右侧不要边框，右栏卡片左侧圆角归零
sub(A,
    """  display: flex; align-items: stretch; gap: var(--sp-2);
  min-width: 0; min-height: 0;""",
    """  display: flex; align-items: stretch; gap: 0;
  min-width: 0; min-height: 0;""",
    "右栏去间隙")

sub(A,
    """  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-surface); color: var(--text-muted);""",
    """  /* 和右边的卡片连成一体：右侧不要边框，左边圆角、右边直角 */
  border: 1px solid var(--border); border-right: 0;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
  background: var(--bg-surface); color: var(--text-muted);""",
    "把手样式")

# 右栏里的卡片左侧圆角归零（与把手拼接）
s = load(A)
if ".right-stack > .card:first-child" not in s:
    idx = s.rfind("</style>")
    add = """
/* 右栏第一张卡片与把手拼接：左侧圆角归零，看起来是同一个容器 */
.right-stack > :first-child {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}
"""
    save(A, s[:idx] + add + s[idx:])
    print("  ok   右栏卡片左圆角归零")

# 5) WorldMap 里删掉原控件块（已挪走），头部只剩标题与一行描述
W = "web/src/components/WorldMap.vue"
s = load(W)
m = re.search(r'\n      <div class="ctrls">[\s\S]*?\n      </div>\n', s)
if m:
    save(W, s[:m.start()] + "\n" + s[m.end():])
    print("  ok   WorldMap 移除控件块")
else:
    print("  MISS WorldMap 控件块")
