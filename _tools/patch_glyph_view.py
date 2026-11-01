"""WorldMap：复合字形的计算、绘制、图例三态与开关面板。"""

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


# ---------------------------------------------------------------- 1) contextData
rep(
    """  // ---------- 近景：一个语言一个点 ----------
  if (!store.mapDensity) {""",
    """  // 字形模式下底图不由这个 computed 提供（见 glyphItems），避免和字形重复绘制
  if (store.mapMode === 'glyph') return []

  // ---------- 近景：一个语言一个点 ----------
  if (store.mapMode === 'dots') {""",
    "contextData 三态",
)

# ---------------------------------------------------------------- 2) 字形计算
GLYPH_BLOCK = '''
/* --------------------------------------------------------------- 复合字形 */
/**
 * 一门语言 = 一个由部件组成的小符号（glyph）。
 *
 * 思路借自 GlottoVis：用字形的**不同部位**分别编码不同维度，
 * 而不是「一个点只编码一个变量」。本项目的部件分配：
 *
 *   外环颜色  ← 濒危等级（AES 1–6）
 *   环内扇形  ← 描写深度（1–5，扇形张角 = depth/5 圈）
 *   中心点    ← 是否有维基百科版本（实心 = 有）
 *   字形大小  ← 当月浏览量（对数）
 *   外围刻度  ← 维基百科之外还拥有几个维基项目（0–7 根）
 *
 * 每个通道都能单独关掉。关掉时**用中性灰继续画**，而不是不画 ——
 * 这样"关掉这个维度"的代价是看得见的：地图会立刻灰掉一片。
 */
const GLYPH_RAMP = ['#7c9a6a', '#c9b458', '#d9964a', '#cf6b3f', '#b34a35', '#7d3226']

interface GlyphItem {
  lng: number
  lat: number
  r: number
  ringColor: string
  ringW: number
  arcFrac: number
  arcColor: string
  coreFill: string
  coreStroke: string
  ticks: number
  opacity: number
  // 供 tooltip 与点击使用，字段与其它图层保持一致
  name: string
  display: string
  wals_id: string
  macroarea: string | null
  family: string
  views?: number
  growth?: number | null
  baseline_ok?: boolean
}

/**
 * 所有颜色与半径都在这里算好。
 * renderItem 会对每个元素调用一次（世界视图下是 2,662 次），
 * 里面不能做查表和开方以外的运算。
 */
const glyphItems = computed<GlyphItem[]>(() => {
  const ch = store.glyphChannels
  const depth = store.descDepth
  const proj = store.wikiProjects
  const ebw = store.endangermentByWals
  const sel = store.selected
  const inFam = famIds.value
  const matched = store.matchedIds
  const filtering = store.hasFilter
  const maxV = Math.max(1, ...store.withVitality.map((l) => l.views_recent ?? 0))
  const logMax = Math.log10(1 + maxV)
  const out: GlyphItem[] = []
  for (const l of store.langs) {
    if (!hasCoords(l)) continue
    if (!keepLang(l.wals_id)) continue
    const isSel = sel === l.wals_id
    const hit = !filtering || matched.has(l.wals_id)
    const lv = ebw[l.wals_id]
    const d = depth[l.wals_id]
    const pj = proj[l.wals_id]
    const fam = inFam?.has(l.wals_id) ?? false
    // 大小 ← 浏览量
    let r = 5
    if (ch.size) {
      const v = l.views_recent ?? 0
      r = 4 + (Math.log10(1 + v) / logMax) * 9
    }
    out.push({
      lng: Number(l.longitude),
      lat: Number(l.latitude),
      r: isSel ? r + 2 : r,
      ringColor: ch.ring && lv ? GLYPH_RAMP[lv - 1] : (isSel || fam ? C.accent : '#D2C9BA'),
      ringW: isSel ? 2.6 : fam ? 1.9 : 1.3,
      arcFrac: ch.arc && d ? d.depth / 5 : 0,
      arcColor: fam ? 'rgba(228,87,46,.85)' : 'rgba(228,87,46,.5)',
      coreFill: ch.core && l.wiki_code ? C.accent : 'rgba(0,0,0,0)',
      coreStroke: ch.core && l.wiki_code ? C.accent : '#BFB5A3',
      ticks: ch.ticks && pj ? Math.min(pj.n_extra, 7) : 0,
      opacity: isSel ? 1 : hit ? (filtering ? 0.95 : 0.82) : 0.12,
      name: l.name,
      display: langLabel(l),
      wals_id: l.wals_id,
      macroarea: l.macroarea,
      family: l.family || '—',
      views: l.views_recent ?? undefined,
      growth: l.growth,
      baseline_ok: l.baseline_ok,
    })
  }
  return out
})

/**
 * custom series 的绘制函数。坐标系是 geo，`api.coord` 负责经纬度 → 像素。
 * 所有子图形都用**绝对像素**坐标（cx/cy 就是 pt），不依赖 group 的位移。
 */
function renderGlyph(params: any, api: any) {
  const it = glyphItems.value[params.dataIndex]
  if (!it) return null
  const pt = api.coord([it.lng, it.lat])
  if (!pt || !Number.isFinite(pt[0]) || !Number.isFinite(pt[1])) return null
  const x = pt[0]
  const y = pt[1]
  const r = it.r
  const kids: any[] = []
  kids.push({
    type: 'circle',
    shape: { cx: x, cy: y, r },
    style: { fill: 'none', stroke: it.ringColor, lineWidth: it.ringW, opacity: it.opacity },
  })
  if (it.arcFrac > 0) {
    kids.push({
      type: 'sector',
      shape: {
        cx: x, cy: y, r: Math.max(r - 2.2, 1.5), r0: 0,
        startAngle: -Math.PI / 2,
        endAngle: -Math.PI / 2 + Math.PI * 2 * it.arcFrac,
      },
      style: { fill: it.arcColor, opacity: it.opacity * 0.6 },
    })
  }
  kids.push({
    type: 'circle',
    shape: { cx: x, cy: y, r: Math.max(1.1, r * 0.3) },
    style: {
      fill: it.coreFill, stroke: it.coreStroke, lineWidth: 1,
      opacity: it.opacity,
    },
  })
  for (let i = 0; i < it.ticks; i++) {
    const a = -Math.PI / 2 + (Math.PI * 2 * i) / it.ticks
    kids.push({
      type: 'line',
      shape: {
        x1: x + Math.cos(a) * (r + 1.5), y1: y + Math.sin(a) * (r + 1.5),
        x2: x + Math.cos(a) * (r + 3.4), y2: y + Math.sin(a) * (r + 3.4),
      },
      style: { stroke: '#9A9184', lineWidth: 1, opacity: it.opacity * 0.9 },
    })
  }
  return { type: 'group', children: kids }
}

/** 开关面板的五个通道（标签与说明都进 i18n） */
const CHANNELS = computed(() => [
  { key: 'ring' as const, label: t.value.chRing, dim: t.value.dRing },
  { key: 'arc' as const, label: t.value.chArc, dim: t.value.dArc },
  { key: 'core' as const, label: t.value.chCore, dim: t.value.dCore },
  { key: 'size' as const, label: t.value.chSize, dim: t.value.dSize },
  { key: 'ticks' as const, label: t.value.chTicks, dim: t.value.dTicks },
])

function toggleChannel(key: keyof typeof store.glyphChannels, e: Event) {
  const on = (e.target as HTMLInputElement).checked
  store.glyphChannels[key] = on
}

'''

rep(
    "const isAgg = computed(() => store.mapDensity)",
    GLYPH_BLOCK + "const isAgg = computed(() => store.mapMode === 'density')",
    "插入字形计算",
)

# ---------------------------------------------------------------- 3) 系列
rep(
    "  return [famHullSeries, famStarSeries, famGlowSeries, ctx, vit, halo]",
    """  // 复合字形层。因为要接 tooltip 与点击，所以不是 silent；
  // data 里带上与其它图层相同的字段，tooltip 的 formatter 不用特判。
  const glyphSeries = {
    id: 'glyph', name: 'glyph', type: 'custom', coordinateSystem: 'geo',
    renderItem: renderGlyph,
    encode: { x: 0, y: 1 },
    data: store.mapMode === 'glyph'
      ? glyphItems.value.map((g) => ({
        value: [g.lng, g.lat],
        name: g.name, display: g.display, wals_id: g.wals_id,
        macroarea: g.macroarea, family: g.family,
        views: g.views, growth: g.growth, baseline_ok: g.baseline_ok,
      }))
      : [],
    z: 1.2, progressive: 0, animation: false,
  }
  return [famHullSeries, famStarSeries, famGlowSeries, ctx, glyphSeries, vit, halo]""",
    "加入字形系列",
)

# ---------------------------------------------------------------- 4) 重绘监听
rep(
    "watch([contextData, vitalityData, haloData, famStar, famHull, famGlow], () => render(false))",
    "watch([contextData, vitalityData, haloData, famStar, famHull, famGlow, glyphItems],\n"
    "  () => render(false))",
    "重绘监听",
)

# ---------------------------------------------------------------- 5) 图例三态
rep(
    """        <button class="seg" :class="{ on: isAgg }" @click="store.mapDensity = true">{{ t.densityBtn }}</button>
        <button class="seg" :class="{ on: !isAgg }" @click="store.mapDensity = false">{{ t.dotsBtn }}</button>""",
    """        <button class="seg" :class="{ on: isAgg }" @click="store.mapMode = 'density'">{{ t.densityBtn }}</button>
        <button class="seg" :class="{ on: store.mapMode === 'dots' }" @click="store.mapMode = 'dots'">{{ t.dotsBtn }}</button>
        <button class="seg" :class="{ on: store.mapMode === 'glyph' }" @click="store.mapMode = 'glyph'">{{ t.glyphBtn }}</button>""",
    "图例三态",
)

# ---------------------------------------------------------------- 6) 开关面板
rep(
    '    <div ref="host" class="chart" />',
    '''    <div ref="host" class="chart" />

    <!-- 字形通道开关：浮在地图左上角，只在字形模式下出现 -->
    <div v-if="store.mapMode === 'glyph'" class="channels">
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
    </div>''',
    "开关面板模板",
)

# ---------------------------------------------------------------- 7) 样式
rep(
    ".legend .seg.on { background: var(--accent); border-color: var(--accent); color: var(--text-inverse); }",
    """.legend .seg.on { background: var(--accent); border-color: var(--accent); color: var(--text-inverse); }

/* ---- 字形通道开关 ---- */
.card { position: relative; }
.channels {
  position: absolute; left: 16px; top: 96px; width: 246px; z-index: 6;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--border); border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 10px 12px 11px;
  backdrop-filter: blur(6px);
}
.ch-head {
  margin: 0 0 8px; font-size: var(--fs-micro); font-weight: 600;
  color: var(--text-secondary); line-height: 1.5;
}
.ch-head span { display: block; font-weight: 400; color: var(--text-muted); }
.ch {
  display: flex; align-items: flex-start; gap: 7px;
  padding: 3px 0; cursor: pointer; user-select: none;
}
.ch input { position: absolute; opacity: 0; width: 0; height: 0; }
.ch-box {
  flex: none; width: 13px; height: 13px; margin-top: 2px;
  border: 1.5px solid var(--border-strong); border-radius: 3px;
  background: var(--bg-surface); position: relative;
  transition: background var(--dur-fast) var(--ease-out);
}
.ch input:checked + .ch-box { background: var(--accent); border-color: var(--accent); }
.ch input:checked + .ch-box::after {
  content: ""; position: absolute; left: 3.4px; top: 0.6px;
  width: 4px; height: 7.5px; border: solid #fff;
  border-width: 0 1.8px 1.8px 0; transform: rotate(42deg);
}
.ch-txt { display: flex; flex-direction: column; line-height: 1.35; }
.ch-txt b { font-size: var(--fs-micro); font-weight: 600; color: var(--text-secondary); }
.ch-txt i {
  font-style: normal; font-size: 10px; color: var(--text-muted);
}""",
    "开关面板样式",
)

# ---------------------------------------------------------------- 8) 文案
rep(
    "    densityBtn: '密度块',\n    dotsBtn: '逐点',",
    """    densityBtn: '密度块',
    dotsBtn: '逐点',
    glyphBtn: '字形',
    chTitle: '字形部件',
    chHint: '关掉一个维度，看地图还剩多少信息',
    chRing: '外环颜色', dRing: '← 濒危等级',
    chArc: '环内扇形', dArc: '← 描写深度',
    chCore: '中心点', dCore: '← 有无维基版本',
    chSize: '字形大小', dSize: '← 当月浏览量',
    chTicks: '外围刻度', dTicks: '← 其他维基项目数',""",
    "中文文案",
)
rep(
    "    densityBtn: 'Density',\n    dotsBtn: 'Dots',",
    """    densityBtn: 'Density',
    dotsBtn: 'Dots',
    glyphBtn: 'Glyphs',
    chTitle: 'Glyph channels',
    chHint: 'switch a dimension off and see how much is left',
    chRing: 'Outer ring', dRing: '← endangerment',
    chArc: 'Inner wedge', dArc: '← description depth',
    chCore: 'Centre dot', dCore: '← has Wikipedia',
    chSize: 'Glyph size', dSize: '← monthly views',
    chTicks: 'Outer ticks', dTicks: '← other wiki projects',""",
    "英文文案",
)

# ---------------------------------------------------------------- 9) 钻取
rep("          store.mapDensity = false", "          store.mapMode = 'dots'", "钻取切模式")

io.open(P, "w", encoding="utf-8").write(s)
print("  写入完成")
