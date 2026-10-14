<script setup lang="ts">
/**
 * M4 记录缺口图：数据集本身的结构。
 *
 * 为什么值得单独做一个视图：WALS 的 2,660 × 192 矩阵**只有 15% 有值**，
 * 特征覆盖率中位数仅 9.7%。这种"记录的不平等"本身就是发现：
 *
 *   WALS 收录 <30 个特征的语言：1,662 门，其中仅  5.7% 有维基版本
 *   WALS 收录 ≥150 个特征的语言：   14 门，其中 92.9% 有维基版本
 *
 * 也就是 —— **语言学界记录得越少的语言，在数字世界里往往也越不可见。**
 *
 * 视图分两块：
 *   上：记录密度矩阵。x = 192 个特征（按覆盖率降序），y = 语言（按记录完整度降序）。
 *       每格颜色 = 该行语言组中"有这条特征记录"的比例。左上密、右下空，
 *       这个阶梯形状就是"记录集中在少数语言与少数特征上"的视觉形态。
 *   下：双重缺席。按记录完整度分桶，看有维基版本的比例如何陡增。
 *
 * 用 canvas 手绘而非 ECharts：2660 × 192 = 51 万格，heatmap 系列扛不住。
 * 先画进一张 cols×rows 的离屏画布，再缩放贴上来 —— 顺带得到密度图该有的平滑感。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { semanticColors, sequentialScale } from '@/theme/echarts-theme.js'

const store = useDataset()
const { feature: featureLabel } = useDisplayNames()
const C = semanticColors()

const host = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const hover = ref<{ x: number; y: number; col: number; row: number } | null>(null)

/** 纵向分箱数。1 箱约 6-7 门语言，画出来刚好是密度图而不是噪点 */
const BINS = 380

const T = {
  zh: {
    title: '记录缺口图',
    sub: '本视图展示数据集自身的结构，不响应左侧筛选 · 颜色 = 该组语言中「有这条特征记录」的比例',
    axisX: '横向 192 个语法特征，按覆盖率从高到低',
    axisY: '纵向 2,660 门语言，按被记录的特征数从多到少',
    cellHint: '每一格不是一门语言，而是「这一横条里的语言」中有该特征记录的**比例**',
    byCoverage: '按记录完整度',
    byFamily: '按语系',
    featCoverage: '覆盖率',
    langs: '语言',
    withData: '有记录',
    clickHint: '点一下按该特征筛选全站',
    filtered: '右侧灰条 = 命中筛选的语言在这条排序里的位置',
    filterOn: (n: string, name: string) => `已按「${name}」筛选：全站只剩 ${n} 门有该特征记录的语言`,
    clear: '清除',
    absence: '双重缺席',
    absenceSub: '按 WALS 记录完整度分桶，看拥有维基百科版本的比例',
    bucket: 'WALS 收录特征数',
    hasWiki: '有维基版本',
    finding: '语言学界记录得越少的语言，在数字世界里往往也越不可见。',
  },
  en: {
    title: 'Documentation gaps',
    sub: 'This view shows the dataset’s own structure and does not follow the left-hand filters · colour = share of languages in the band that have this feature recorded',
    axisX: '192 grammatical features across, most-covered on the left',
    axisY: '2,660 languages down, best-documented at the top',
    cellHint: 'a cell is not one language — it is the **share** of languages in that row band that have this feature recorded',
    byCoverage: 'By coverage',
    byFamily: 'By family',
    featCoverage: 'Coverage',
    langs: 'languages',
    withData: 'recorded',
    clickHint: 'click to filter the whole dashboard by this feature',
    filtered: 'grey strip on the right = where matching languages sit in this ranking',
    filterOn: (n: string, name: string) => `Filtered by “${name}”: ${n} languages have it recorded`,
    clear: 'clear',
    absence: 'Double absence',
    absenceSub: 'Binned by WALS coverage; share that have a Wikipedia edition',
    bucket: 'WALS features recorded',
    hasWiki: 'has Wikipedia',
    finding: 'The less a language is documented by linguistics, the less visible it tends to be digitally.',
  },
} as const
const t = computed(() => T[store.lang])

/* ----------------------------------------------------------------- 数据准备 */

const featIds = computed(() => store.matrix?.feature_ids ?? [])

/** 每个特征的覆盖数 */
const featCount = computed(() => {
  const m = store.matrix
  if (!m) return [] as number[]
  return m.values.map((row) => {
    let n = 0
    for (let i = 0; i < row.length; i++) if (row[i] != null) n++
    return n
  })
})

/** 列序：覆盖率降序 —— 阶梯形状靠它显现 */
const colOrder = computed(() => {
  const c = featCount.value
  return c.map((_, i) => i).sort((a, b) => c[b] - c[a] || a - b)
})

/** colOrder 的逆映射：特征下标 → 列位置。用来把「当前筛选的特征」画成一条明确的竖线 */
const colPos = computed(() => {
  const inv: number[] = []
  colOrder.value.forEach((fi, pos) => { inv[fi] = pos })
  return inv
})

/** 当前筛选的特征（用于画高亮竖线与顶部提示条） */
const activeFeature = computed(() => {
  const cur = store.featureFilter
  if (!cur) return null
  const m = store.matrix
  if (!m) return null
  const fi = m.feature_ids.indexOf(cur.featureId)
  if (fi < 0) return null
  const name = featureLabel(
    cur.featureId,
    store.features?.features.find((f) => f.ID === cur.featureId)?.Name ?? cur.featureId)
  const hit = store.filtered.length
  const total = m.language_keys.length
  return { fid: cur.featureId, name, hit, total, pos: colPos.value[fi] ?? -1 }
})

const sortBy = ref<'coverage' | 'family'>('coverage')

/** 行序：记录完整度降序；按语系时先按语区再按语系再按完整度 */
const rowOrder = computed(() => {
  const m = store.matrix
  if (!m) return [] as number[]
  const fc = store.featureCount
  const idx = m.language_keys.map((_, i) => i)
  const byId = new Map(store.langs.map((l) => [l.wals_id, l]))
  const keyOf = (i: number) => {
    const l = byId.get(m.language_keys[i])
    return l ? `${l.macroarea ?? '~'}|${l.family ?? '~'}` : '~~'
  }
  if (sortBy.value === 'family') {
    return idx.sort((a, b) => {
      const ka = keyOf(a)
      const kb = keyOf(b)
      if (ka !== kb) return ka < kb ? -1 : 1
      return (fc[m.language_keys[b]] ?? 0) - (fc[m.language_keys[a]] ?? 0)
    })
  }
  return idx.sort((a, b) =>
    (fc[m.language_keys[b]] ?? 0) - (fc[m.language_keys[a]] ?? 0))
})

/**
 * 密度网格：grid[row * cols + col] = 该行语言组中列特征有记录的比例。
 * 只依赖数据与排序，不依赖鼠标，所以可以缓存下来只在必要时重算。
 */
const grid = computed(() => {
  const m = store.matrix
  if (!m) return { data: new Float32Array(0), cols: 0, rows: 0 }
  const cols = m.feature_ids.length
  const rows = BINS
  const order = rowOrder.value
  const out = new Float32Array(cols * rows)
  const per = order.length / rows
  // 每一行箱覆盖 [r*per, (r+1)*per) 范围内的语言
  for (let r = 0; r < rows; r++) {
    const lo = Math.floor(r * per)
    const hi = Math.max(Math.floor((r + 1) * per), lo + 1)
    const n = hi - lo
    if (n <= 0) continue
    for (let c = 0; c < cols; c++) {
      const row = m.values[c]
      let hit = 0
      for (let k = lo; k < hi && k < order.length; k++) {
        if (row[order[k]] != null) hit++
      }
      out[r * cols + c] = hit / n
    }
  }
  return { data: out, cols, rows }
})

/** 当前筛选命中的语言落在哪些行箱里（画右侧标记条用） */
const filterBins = computed(() => {
  const m = store.matrix
  if (!m || !store.hasFilter) return null
  const matched = store.matchedIds
  const order = rowOrder.value
  const per = order.length / BINS
  const bins = new Uint8Array(BINS)
  for (let r = 0; r < BINS; r++) {
    const lo = Math.floor(r * per)
    const hi = Math.max(Math.floor((r + 1) * per), lo + 1)
    for (let k = lo; k < hi && k < order.length; k++) {
      if (matched.has(m.language_keys[order[k]])) { bins[r] = 1; break }
    }
  }
  return bins
})

/* ------------------------------------------------------------- 双重缺席统计 */

const absence = computed(() => {
  const fc = store.featureCount
  const buckets = [
    { lo: 0, hi: 30, label: '< 30' },
    { lo: 30, hi: 80, label: '30–79' },
    { lo: 80, hi: 150, label: '80–149' },
    { lo: 150, hi: Infinity, label: '≥ 150' },
  ]
  return buckets.map((b) => {
    const rows = store.langs.filter((l) => {
      const c = fc[l.wals_id] ?? 0
      return c >= b.lo && c < b.hi
    })
    const wiki = rows.filter((l) => l.wiki_code).length
    return {
      label: b.label,
      n: rows.length,
      wiki,
      rate: rows.length ? wiki / rows.length : 0,
    }
  })
})

/* ------------------------------------------------------------------- 绘制 */

/** 把 0..1 映射到顺序色阶（四段线性插值） */
function ramp(v: number): [number, number, number] {
  const s = sequentialScale()
  const hex = (h: string) => [
    parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16),
  ]
  const stops = s.map(hex)
  const x = Math.min(Math.max(v, 0), 1) * (stops.length - 1)
  const i = Math.min(Math.floor(x), stops.length - 2)
  const f = x - i
  const a = stops[i]
  const b = stops[i + 1]
  return [
    Math.round(a[0] + (b[0] - a[0]) * f),
    Math.round(a[1] + (b[1] - a[1]) * f),
    Math.round(a[2] + (b[2] - a[2]) * f),
  ]
}

let off: HTMLCanvasElement | null = null
let raf = 0

function draw() {
  const cv = canvas.value
  const box = host.value
  if (!cv || !box) return
  const W = box.clientWidth
  const H = box.clientHeight
  if (W <= 0 || H <= 0) return

  const dpr = window.devicePixelRatio || 1
  cv.width = Math.round(W * dpr)
  cv.height = Math.round(H * dpr)
  cv.style.width = `${W}px`
  cv.style.height = `${H}px`
  const ctx = cv.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, W, H)

  const { data, cols, rows } = grid.value
  if (!cols || !rows) return

  // 先画到 cols×rows 的离屏画布，再缩放贴上来
  if (!off) off = document.createElement('canvas')
  off.width = cols
  off.height = rows
  const octx = off.getContext('2d')
  if (!octx) return
  const img = octx.createImageData(cols, rows)
  // 缓存色阶查表：0..1 量化成 256 级，避免 8 万次插值
  const lut: [number, number, number][] = []
  for (let i = 0; i < 256; i++) lut.push(ramp(i / 255))
  for (let i = 0; i < cols * rows; i++) {
    const [r, g, b] = lut[Math.round(data[i] * 255)]
    img.data[i * 4] = r
    img.data[i * 4 + 1] = g
    img.data[i * 4 + 2] = b
    img.data[i * 4 + 3] = 255
  }
  octx.putImageData(img, 0, 0)
  ctx.imageSmoothingEnabled = true
  ctx.drawImage(off, 0, 0, W, H)

  // 按语系排序时画分组分隔线，否则一整片看不出结构
  if (sortBy.value === 'family') {
    const m = store.matrix
    const order = rowOrder.value
    if (m) {
      const byId = new Map(store.langs.map((l) => [l.wals_id, l]))
      const keyOf = (i: number) => {
        const l = byId.get(m.language_keys[i])
        return l ? `${l.macroarea ?? '~'}|${l.family ?? '~'}` : '~~'
      }
      ctx.strokeStyle = 'rgba(255,255,255,0.55)'
      ctx.lineWidth = 1
      for (let r = 1; r < rows; r++) {
        const per = order.length / rows
        const a = keyOf(order[Math.floor((r - 1) * per)] ?? 0)
        const b = keyOf(order[Math.min(Math.floor(r * per), order.length - 1)] ?? 0)
        if (a !== b) {
          ctx.beginPath()
          ctx.moveTo(0, (r / rows) * H)
          ctx.lineTo(W, (r / rows) * H)
          ctx.stroke()
        }
      }
    }
  }

  // 当前筛选命中的语言位置：右侧一条标记
  const bins = filterBins.value
  if (bins) {
    ctx.fillStyle = 'rgba(35,32,28,0.55)'
    for (let r = 0; r < rows; r++) {
      if (bins[r]) ctx.fillRect(W - 4, (r / rows) * H, 4, Math.max(H / rows, 1))
    }
  }

  // 当前筛选的**特征列**：画一条明确的竖线。
  // 没有这个的话，点完只在右边多一小条灰，视图内几乎看不出点了哪一列，
  // 而实际筛选效果发生在别的视图里 —— 用户会完全不知道发生了什么。
  const af = activeFeature.value
  if (af && af.pos >= 0) {
    const cw = W / cols
    ctx.strokeStyle = C.accent
    ctx.lineWidth = 2
    ctx.strokeRect(af.pos * cw - 1, 0, cw + 2, H)
  }

  // 悬停十字线
  const hv = hover.value
  if (hv) {
    const cw = W / cols
    const ch = H / rows
    ctx.strokeStyle = 'rgba(35,32,28,0.75)'
    ctx.lineWidth = 1
    ctx.strokeRect(Math.floor(hv.col) * cw, 0, cw, H)
    ctx.strokeRect(0, Math.floor(hv.row) * ch, W, ch)
  }
}

function schedule() {
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(draw)
}

/* ------------------------------------------------------------------- 交互 */

function onMove(ev: MouseEvent) {
  const box = host.value
  if (!box) return
  const rect = box.getBoundingClientRect()
  const x = ev.clientX - rect.left
  const y = ev.clientY - rect.top
  const { cols, rows } = grid.value
  if (!cols || !rows) return
  hover.value = {
    x, y,
    col: Math.min(Math.floor((x / rect.width) * cols), cols - 1),
    row: Math.min(Math.floor((y / rect.height) * rows), rows - 1),
  }
  schedule()
}

function onLeave() {
  hover.value = null
  schedule()
}

function onClick() {
  const hv = hover.value
  const { cols } = grid.value
  if (!hv || !cols) return
  const fid = featIds.value[colOrder.value[hv.col]]
  if (!fid) return
  // 再次点击同一特征则取消（value=null 表示"只要有该特征的记录"）
  const cur = store.featureFilter
  if (cur && cur.featureId === fid && cur.value == null) {
    store.featureFilter = null
  } else {
    store.featureFilter = { featureId: fid, value: null }
    store.compareFeature = fid
  }
}

/** 悬停时显示的那一列特征与那一行语言组 */
const hoverInfo = computed(() => {
  const hv = hover.value
  const m = store.matrix
  if (!hv || !m) return null
  const fi = colOrder.value[hv.col]
  const fid = m.feature_ids[fi]
  const order = rowOrder.value
  const per = order.length / BINS
  const lo = Math.floor(hv.row * per)
  const hi = Math.max(Math.floor((hv.row + 1) * per), lo + 1)
  const ids = order.slice(lo, hi).map((i) => m.language_keys[i])
  const row = m.values[fi]
  const hit = ids.filter((_, k) => row[order[lo + k]] != null).length
  const cov = featCount.value[fi] ?? 0
  return {
    fid,
    name: featureLabel(fid, store.features?.features.find((f) => f.ID === fid)?.Name ?? fid),
    cov, total: m.language_keys.length,
    band: ids.length, hit,
  }
})

/* --------------------------------------------------------------- 生命周期 */

let ro: ResizeObserver | null = null
onMounted(() => {
  schedule()
  if (host.value && typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(schedule)
    ro.observe(host.value)
  }
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  ro?.disconnect()
})

// 数据 / 排序 / 筛选变化都要重画
watch(() => [grid.value, sortBy.value, filterBins.value, store.lang], schedule)
</script>

<template>
  <section class="card">
    <header>
      <div class="tl">
        <h2>{{ t.title }}</h2>
        <p class="hint">{{ t.sub }}</p>
      </div>
      <div class="seg">
        <button :class="{ on: sortBy === 'coverage' }" @click="sortBy = 'coverage'">
          {{ t.byCoverage }}
        </button>
        <button :class="{ on: sortBy === 'family' }" @click="sortBy = 'family'">
          {{ t.byFamily }}
        </button>
      </div>
    </header>

    <div class="axes">
      <span class="ay">↓ {{ t.axisY }}</span>
      <span class="ax">→ {{ t.axisX }}</span>
    </div>

    <div
      ref="host" class="matrix"
      @mousemove="onMove" @mouseleave="onLeave" @click="onClick"
    >
      <canvas ref="canvas" />
      <div
        v-if="hoverInfo && hover"
        class="tip"
        :style="{
          left: Math.min(hover.x + 14, (host?.clientWidth ?? 400) - 230) + 'px',
          top: Math.max(hover.y - 54, 4) + 'px',
        }"
      >
        <strong>{{ hoverInfo.name }}</strong>
        <span class="k">{{ hoverInfo.fid }} · {{ t.featCoverage }}
          <b class="num">{{ hoverInfo.cov.toLocaleString('en-US') }}</b>
          / {{ hoverInfo.total.toLocaleString('en-US') }}
          ({{ (hoverInfo.cov / hoverInfo.total * 100).toFixed(1) }}%)</span>
        <span class="k">{{ t.langs }} {{ hoverInfo.band }} · {{ t.withData }}
          <b class="num">{{ hoverInfo.hit }}</b></span>
        <span class="go">{{ t.clickHint }}</span>
      </div>
    </div>

    <!-- 点击后的反馈条：明确告诉用户"筛选了什么、剩下多少"，并提供一键清除。
         没有它的话，点完只在右边多一小条灰，而效果发生在别的视图里。 -->
    <div v-if="activeFeature" class="filterbar">
      <span class="dot" />
      <span class="ftext">{{ t.filterOn(activeFeature.hit.toLocaleString('en-US'), activeFeature.name) }}</span>
      <span class="num fnum">({{ activeFeature.fid }} · {{ (activeFeature.hit / activeFeature.total * 100).toFixed(1) }}%)</span>
      <button @click="store.featureFilter = null">{{ t.clear }}</button>
    </div>

    <div class="legend">
      <span class="lab">{{ t.withData }}</span>
      <span class="grad" />
      <span class="num">0%</span><span class="num">100%</span>
      <span v-if="filterBins" class="mark"><i />{{ t.filtered }}</span>
    </div>
    <p class="cellhint">{{ t.cellHint }}</p>

    <!-- 双重缺席：这个视图真正的结论 -->
    <div class="absence">
      <div class="ah">
        <h3>{{ t.absence }}</h3>
        <span class="sub">{{ t.absenceSub }}</span>
      </div>
      <div class="bars">
        <div v-for="b in absence" :key="b.label" class="bar">
          <span class="bl num">{{ b.label }}</span>
          <span class="track">
            <i :style="{ width: (b.rate * 100).toFixed(1) + '%' }" />
          </span>
          <span class="bv num">{{ (b.rate * 100).toFixed(1) }}%</span>
          <span class="bn num">{{ b.wiki }}/{{ b.n }}</span>
        </div>
      </div>
      <p class="finding">{{ t.finding }}</p>
    </div>
  </section>
</template>

<style scoped>
.card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--sp-4); display: flex; flex-direction: column;
  gap: var(--sp-2); min-height: 0; height: 100%; overflow: hidden;
}
header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-3); flex: none; }
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 0; font-size: var(--fs-small); color: var(--text-muted); }
.seg { display: flex; border: 1px solid var(--border); border-radius: var(--radius-pill); overflow: hidden; flex: none; }
.seg button {
  border: 0; background: transparent; cursor: pointer; white-space: nowrap;
  padding: 4px 11px; font-size: var(--fs-micro); color: var(--text-secondary); font-family: inherit;
}
.seg button:hover { background: var(--bg-subtle); }
.seg button.on { background: var(--accent); color: var(--text-inverse); }

.matrix { position: relative; flex: 1; min-height: 0; cursor: crosshair; }
.matrix canvas { display: block; border-radius: var(--radius-sm); }

/* 坐标系标注：只给颜色不给坐标含义，读者无从下手（实测被问到过） */
.axes {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: var(--sp-3); flex: none;
  font-size: var(--fs-micro); color: var(--text-muted);
}
.axes .ay { color: var(--text-secondary); }
.axes .ax { color: var(--text-secondary); }

/* 点击后的反馈条 */
.filterbar {
  display: flex; align-items: center; gap: var(--sp-2); flex: none;
  padding: 5px 10px; border-radius: var(--radius-md);
  background: var(--accent-soft);
}
.filterbar .dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--accent); flex: none;
}
.filterbar .ftext { font-size: var(--fs-small); color: var(--text-primary); }
.filterbar .fnum { font-size: var(--fs-micro); color: var(--text-muted); }
.filterbar button {
  margin-left: auto; flex: none; cursor: pointer;
  border: 1px solid var(--accent); border-radius: var(--radius-pill);
  background: transparent; color: var(--accent);
  font-family: inherit; font-size: var(--fs-micro); padding: 2px 10px;
}
.filterbar button:hover { background: var(--accent); color: var(--text-inverse); }

.cellhint { margin: var(--sp-1) 0 0; font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.5; }
.tip {
  position: absolute; z-index: 3; pointer-events: none;
  width: 224px; padding: 7px 10px;
  background: var(--bg-surface); border: 1px solid var(--border-strong);
  border-radius: var(--radius-md); box-shadow: var(--shadow-md);
  display: flex; flex-direction: column; gap: 2px;
}
.tip strong { font-size: var(--fs-small); line-height: 1.35; }
.tip .k { font-size: var(--fs-micro); color: var(--text-muted); }
.tip .k b { color: var(--text-primary); }
.tip .go { font-size: var(--fs-micro); color: var(--accent); }

.legend {
  display: flex; align-items: center; gap: var(--sp-2); flex: none;
  font-size: var(--fs-micro); color: var(--text-muted);
}
.legend .grad {
  width: 120px; height: 8px; border-radius: 4px;
  background: linear-gradient(90deg, var(--seq-0), var(--seq-1), var(--seq-2), var(--seq-3));
}
.legend .num { font-size: var(--fs-micro); }
.legend .mark { margin-left: auto; display: inline-flex; align-items: center; gap: 4px; }
.legend .mark i { width: 4px; height: 10px; background: rgba(35,32,28,0.55); border-radius: 1px; }

.absence { flex: none; border-top: 1px solid var(--border); padding-top: var(--sp-2); }
.ah { display: flex; align-items: baseline; gap: var(--sp-2); }
.ah h3 {
  margin: 0; font-size: var(--fs-micro); text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600;
}
.ah .sub { font-size: var(--fs-micro); color: var(--text-muted); }
.bars { display: flex; flex-direction: column; gap: 3px; margin-top: var(--sp-2); }
.bar { display: grid; grid-template-columns: 58px 1fr 46px 64px; align-items: center; gap: var(--sp-2); }
.bl { font-size: var(--fs-micro); color: var(--text-secondary); text-align: right; }
.track { height: 9px; background: var(--bg-subtle); border-radius: 5px; overflow: hidden; }
.track i { display: block; height: 100%; background: var(--accent); border-radius: 5px; }
.bv { font-size: var(--fs-micro); color: var(--accent); font-weight: 500; }
.bn { font-size: var(--fs-micro); color: var(--text-muted); }
.finding { margin: var(--sp-2) 0 0; font-size: var(--fs-small); color: var(--text-primary); }
</style>
