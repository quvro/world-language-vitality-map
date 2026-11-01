"""字形通道面板支持收起 —— 用户反馈它挡地图。"""

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


# 1) store：记住收起状态（放 store 是因为切视图会重建组件）
sub("web/src/stores/dataset.ts",
    "  mapMode: 'density' | 'dots' | 'glyph'",
    "  mapMode: 'density' | 'dots' | 'glyph'\n"
    "  /** 字形通道面板是否展开。放 store 而非组件内，切视图回来不会自动弹开 */\n"
    "  glyphPanelOpen: boolean",
    "store 接口")

sub("web/src/stores/dataset.ts",
    "    mapMode: 'density',",
    "    mapMode: 'density',\n    glyphPanelOpen: true,",
    "store 默认值")

# 2) 模板：标题变成可点的收起开关，本体 v-show
OLD = """    <div v-if="store.mapMode === 'glyph'" class="channels">
      <p class="ch-head">
        {{ t.chTitle }}
        <span>{{ t.chHint }}</span>
      </p>
      <label v-for="c in CHANNELS" :key="c.key" class="ch">
        <input
          type="checkbox"
          :checked="store.glyphChannels[c.key]"
          @change="toggleChannel(c.key, $event)"
        >
        <span class="ch-box" />
        <span class="ch-txt">
          <b>{{ c.label }}</b>
          <i>{{ c.dim }}</i>
        </span>
      </label>
    </div>"""

NEW = """    <div v-if="store.mapMode === 'glyph'" class="channels"
         :class="{ folded: !store.glyphPanelOpen }">
      <button class="ch-toggle" @click="store.glyphPanelOpen = !store.glyphPanelOpen">
        <span class="ch-title">{{ t.chTitle }}</span>
        <span class="ch-count num">{{ enabledChannels }}/5</span>
        <span class="chev">{{ store.glyphPanelOpen ? '▾' : '▸' }}</span>
      </button>
      <div v-show="store.glyphPanelOpen" class="ch-body">
        <p class="ch-head">{{ t.chHint }}</p>
        <label v-for="c in CHANNELS" :key="c.key" class="ch">
          <input
            type="checkbox"
            :checked="store.glyphChannels[c.key]"
            @change="toggleChannel(c.key, $event)"
          >
          <span class="ch-box" />
          <span class="ch-txt">
            <b>{{ c.label }}</b>
            <i>{{ c.dim }}</i>
          </span>
        </label>
      </div>
    </div>"""
sub("web/src/components/WorldMap.vue", OLD, NEW, "模板：可收起")

# 3) 计算开着的通道数
sub("web/src/components/WorldMap.vue",
    "function toggleChannel(",
    "/** 开着几个通道 —— 收起时也能一眼看到 */\n"
    "const enabledChannels = computed(\n"
    "  () => Object.values(store.glyphChannels).filter(Boolean).length)\n\n"
    "function toggleChannel(",
    "计算通道数")

# 4) 样式：标题变按钮、收起后只留一行
sub("web/src/components/WorldMap.vue",
    """  padding: 12px 13px 13px;
  backdrop-filter: blur(8px);
}""",
    """  padding: 12px 13px 13px;
  backdrop-filter: blur(8px);
  transition: width var(--dur-fast) var(--ease-out);
}
/* 收起状态：只留一行标题，不再挡地图 */
.channels.folded { width: auto; min-width: 172px; padding: 9px 12px 10px; }
.ch-toggle {
  display: flex; align-items: center; gap: 6px; width: 100%;
  border: 0; background: transparent; padding: 0;
  cursor: pointer; font-family: inherit; text-align: left;
}
.ch-title {
  font-size: var(--fs-small); font-weight: 700; color: var(--text-primary);
}
.ch-count {
  margin-left: auto; font-size: 11px; font-weight: 700; color: var(--accent);
}
.chev { font-size: 11px; color: var(--text-muted); }
.ch-body { margin-top: 9px; padding-top: 7px; border-top: 1px solid var(--border); }
.channels.folded .ch-body { display: none; }""",
    "样式：收起状态")

# 标题在展开时不再重复画分隔线（.ch-body 已经有）
sub("web/src/components/WorldMap.vue",
    """.ch-head {
  margin: 0 0 9px; font-size: var(--fs-small); font-weight: 700;
  color: var(--text-primary); line-height: 1.45;
  padding-bottom: 7px; border-bottom: 1px solid var(--border);
}""",
    """.ch-head {
  margin: 0 0 9px; font-size: var(--fs-micro); font-weight: 400;
  color: var(--text-muted); line-height: 1.5;
}""",
    "样式：说明文字")
