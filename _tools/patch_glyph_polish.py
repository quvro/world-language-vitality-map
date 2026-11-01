"""字形模式的收尾：专属副标题、专属图例，并移除临时探针。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/components/WorldMap.vue"
s = io.open(P, encoding="utf-8").read()


def rep(old, new, tag):
    global s
    if old in s:
        s = s.replace(old, new, 1)
        print(f"  ok   {tag}")
    else:
        print(f"  MISS {tag}")


# 1) 副标题：字形模式有自己的说明
rep(
    "const title = computed(() => store.colorBy === 'trend'",
    """const title = computed(() => store.mapMode === 'glyph'
  ? { t: t.value.distTitle, s: t.value.glyphSub }
  : store.colorBy === 'trend'""",
    "字形副标题",
)

# 2) 图例：字形模式下不用语区图例，改成解释字形部件
rep(
    '''      <template v-if="store.colorBy === 'macroarea'">''',
    '''      <template v-if="store.mapMode === 'glyph'">
        <span class="item gly"><i class="ring" />{{ t.legRing }}</span>
        <span class="item gly"><i class="wedge" />{{ t.legWedge }}</span>
        <span class="item gly"><i class="core" />{{ t.legCore }}</span>
        <span class="item gly"><i class="tick" />{{ t.legTick }}</span>
      </template>
      <template v-else-if="store.colorBy === 'macroarea'">''',
    "字形图例",
)

# 3) 样式
rep(
    "/* ---- 字形通道开关 ---- */",
    """/* ---- 字形图例 ---- */
.legend .gly { color: var(--text-muted); }
.legend .gly i {
  display: inline-block; width: 12px; height: 12px; margin-right: 5px;
  vertical-align: -2px; position: relative;
}
.legend .gly .ring { border: 2px solid var(--accent); border-radius: 50%; }
.legend .gly .wedge {
  border-radius: 50%;
  background: conic-gradient(var(--accent) 0 55%, transparent 55% 100%);
  box-shadow: inset 0 0 0 1.5px var(--border-strong);
}
.legend .gly .core {
  width: 7px; height: 7px; margin: 0 7.5px 0 2.5px;
  background: var(--accent); border-radius: 50%;
}
.legend .gly .tick {
  width: 14px; height: 14px; margin-right: 4px;
  border-radius: 50%;
  border: 1.5px dotted var(--text-muted);
}

/* ---- 字形通道开关 ---- */""",
    "字形图例样式",
)

# 4) 文案
rep(
    "    chTicks: '外围刻度', dTicks: '← 其他维基项目数',",
    """    chTicks: '外围刻度', dTicks: '← 其他维基项目数',
    glyphSub: '一个符号 = 一门语言 · 环色 = 濒危等级 · 扇形 = 描写深度 · '
      + '实心点 = 有维基版本 · 大小 = 当月浏览量 · 刻度 = 其他维基项目',
    legRing: '环 = 濒危', legWedge: '扇形 = 描写深度',
    legCore: '实心 = 有维基', legTick: '刻度 = 项目数',""",
    "字形中文文案",
)
rep(
    "    chTicks: 'Outer ticks', dTicks: '← other wiki projects',",
    """    chTicks: 'Outer ticks', dTicks: '← other wiki projects',
    glyphSub: 'one symbol = one language · ring = endangerment · wedge = description depth '
      + '· filled dot = has Wikipedia · size = monthly views · ticks = other wiki projects',
    legRing: 'ring = endangerment', legWedge: 'wedge = depth',
    legCore: 'filled = has Wikipedia', legTick: 'ticks = projects',""",
    "字形英文文案",
)

io.open(P, "w", encoding="utf-8").write(s)

# 5) 移除 App.vue 里的临时探针
A = "web/src/App.vue"
a = io.open(A, encoding="utf-8").read()
line = "\n  setTimeout(() => { store.mapMode = 'glyph' }, 3000)  // TEMP-PROBE"
if line in a:
    io.open(A, "w", encoding="utf-8").write(a.replace(line, "", 1))
    print("  ok   已移除临时探针")
else:
    print("  !! 探针没找到（可能已被移除）")
