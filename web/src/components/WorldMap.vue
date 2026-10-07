<script setup lang="ts">
/**
 * 世界语言地图。
 *
 * 结构：两个图层始终存在，各司其职
 *   底图 context  : 全部有坐标的语言，小点。负责回答「语言在哪里」。
 *   活力 vitality : 有维基版本的那一批，大小 = 当月浏览量。负责回答「谁在数字空间活着」。
 *
 * 为什么是这个结构：早期版本用「分布 / 活力」两个模式互斥切换整套数据集，
 * 结果在分布模式下拖时间轴**完全没有反应**（那个模式里没有任何时间编码），
 * 切到活力模式地图又会空掉一大半。这是设计缺陷而非 bug，所以直接去掉模式划分：
 * 活力层永远在线，时间轴永远有效。着色依据是另一个正交的开关。
 *
 * 大小用 series 级 `symbolSize` 回调（值里带当月浏览量），而不是逐项 symbolSize
 * 属性 —— 回调每次渲染都会重新求值，更新更可靠，也更容易补间。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { MACRO_AREAS, type MacroArea } from '@/types'
import { categoryPalette, semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)

const e = () => (window as any).echarts
const C = semanticColors()
const PALETTE = categoryPalette()
const macroColor = new Map<string, string>(
  MACRO_AREAS.map((m, i) => [m, PALETTE[i]])
)

/** world.js 是 ECharts 4 格式的注册脚本，必须先用 <script> 注入一次。 */
let worldReady: Promise<void> | null = null
function ensureWorld(): Promise<void> {
  if (worldReady) return worldReady
  worldReady = new Promise<void>((resolve, reject) => {
    if (e()?.getMap('world')) return resolve()
    const s = document.createElement('script')
    s.src = '/vendor/world.js'
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('世界地图数据 /vendor/world.js 加载失败'))
    document.head.appendChild(s)
  })
  return worldReady
}

const trendColor = (g: number | null | undefined, ok?: boolean) =>
  !ok || g == null ? C.neutral : g >= 0 ? C.positive : C.negative

const baseColor = (l: { macroarea: string | null; growth?: number; baseline_ok?: boolean }) =>
  store.colorBy === 'trend'
    ? trendColor(l.growth, l.baseline_ok)
    : (macroColor.get(l.macroarea ?? '') ?? C.neutral)

/** 底图：只随筛选/着色依据变化，不随时间变化 —— 拖时间轴时它不抖。 */
const contextData = computed(() =>
  store.filtered
    .filter((l) => l.latitude && l.longitude)
    .map((l) => {
      const isSel = store.selected === l.wals_id
      const dim = store.selected && !isSel
      return {
        name: l.name, wals_id: l.wals_id,
        value: [l.longitude, l.latitude, isSel ? 1 : 0],
        family: l.family || '—', macroarea: l.macroarea,
        itemStyle: {
          color: store.colorBy === 'trend'
            ? (dim ? C.neutral : C.textMuted)
            : baseColor(l),
          opacity: dim ? 0.12 : (store.colorBy === 'trend' ? 0.28 : 0.5),
        },
      }
    })
)

/** 活力层：按 wals_id 排序，顺序稳定，便于补间。 */
const vitalityData = computed(() => {
  const views = store.currentViews
  return store.withVitality
    .filter((l) => l.latitude && l.longitude && views[l.wals_id] != null)
    .slice()
    .sort((a, b) => (a.wals_id < b.wals_id ? -1 : 1))
    .map((l) => {
      const v = views[l.wals_id]
      const isSel = store.selected === l.wals_id
      const dim = store.selected && !isSel
      return {
        name: l.name, wals_id: l.wals_id,
        // 第三位是当月浏览量，供 symbolSize 回调用
        value: [l.longitude, l.latitude, v, isSel ? 1 : 0],
        views: v, growth: l.growth, baseline_ok: l.baseline_ok,
        macroarea: l.macroarea,
        itemStyle: {
          color: baseColor(l),
          borderColor: isSel ? C.textPrimary : C.surface,
          borderWidth: isSel ? 2 : 1,
          opacity: dim ? 0.1 : 0.68,
        },
      }
    })
})

const maxViews = computed(() => Math.max(store.currentMax, 1))

function tooltipFormatter(p: any) {
  const d = p.data
  if (!d) return ''
  if (d.views == null) {
    return `<strong>${d.name}</strong><br>` +
      `<span style="color:${C.textMuted}">语系</span> ${d.family}<br>` +
      `<span style="color:${C.textMuted}">语区</span> ${d.macroarea ?? '—'}<br>` +
      `<em style="color:${C.textMuted}">没有维基百科版本，无时间序列</em>`
  }
  const g = d.growth == null ? '—'
    : `${d.growth >= 0 ? '+' : ''}${(d.growth * 100).toFixed(1)}%`
  return `<strong>${d.name}</strong><br>` +
    `<span style="color:${C.textMuted}">${store.currentMonth} 浏览</span> ` +
    `${Number(d.views).toLocaleString('en-US')}<br>` +
    `<span style="color:${C.textMuted}">十年趋势</span> ${g}` +
    (d.baseline_ok ? '' : '<br><em style="color:${C.textMuted}">基线过低，趋势不可信</em>')
}

function buildSeries() {
  // 大小走回调：ECharts 每次渲染都重新求值，比逐项 symbolSize 属性更新更可靠
  const vitalitySeries = {
    id: 'vit', name: '数字活力', type: 'scatter', coordinateSystem: 'geo',
    data: store.showVitality ? vitalityData.value : [],
    z: 2,
    emphasis: { scale: 1.25 },
    symbolSize: (val: number[]) => {
      const size = 5 + Math.sqrt(Number(val[2] ?? 0) / maxViews.value) * 34
      return val[3] ? size + 5 : size
    },
  }
  const contextSeries = {
    id: 'ctx', name: '全部语言', type: 'scatter', coordinateSystem: 'geo',
    data: contextData.value,
    z: 1,
    emphasis: { scale: 1.5 },
    symbolSize: (val: number[]) => (val[2] ? 11 : 3.6),
  }
  return [contextSeries, vitalitySeries]
}

const OPT_BASE = {
  tooltip: { trigger: 'item', formatter: tooltipFormatter },
  geo: { map: 'world', roam: true, zoom: 1.15, center: [10, 18] },
}

function render(full = false) {
  if (!chart.value) return
  const series = buildSeries()
  if (full) chart.value.setOption({ ...OPT_BASE, series }, true)
  else chart.value.setOption({ series })
}

const title = computed(() => store.colorBy === 'trend'
  ? { t: '数字活力地图', s: `点的大小 = ${store.currentMonth} 的浏览量 · 颜色 = 十年趋势` }
  : { t: '世界语言分布', s: `小点 = 全部语言（按语区着色）· 大点 = 有维基版本的，大小随 ${store.currentMonth} 的浏览量` }
)

onMounted(async () => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  chart.value.on('click', (p: any) => {
    if (p.data?.wals_id) store.select(p.data.wals_id)
  })
  await ensureWorld()
  render(true)
  window.addEventListener('resize', resize)
})

function resize() { chart.value?.resize() }
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart.value?.dispose()
})

// 结构性变化 → 整幅重绘
watch(() => [store.colorBy, store.showVitality, store.filtered], () => render(true))
// 时间轴 / 选中变化 → merge 更新，点的大小平滑补间
watch(() => [store.monthIndex, store.selected], () => render(false))
</script>

<template>
  <section class="card">
    <header>
      <div>
        <h2>{{ title.t }}</h2>
        <p class="hint">{{ title.s }}</p>
      </div>
      <div class="ctrls">
        <div class="seg">
          <button :class="{ on: store.colorBy === 'macroarea' }" @click="store.colorBy = 'macroarea'">按语区</button>
          <button :class="{ on: store.colorBy === 'trend' }" @click="store.colorBy = 'trend'">按趋势</button>
        </div>
        <label class="chk">
          <input v-model="store.showVitality" type="checkbox">
          <span>活力层</span>
        </label>
      </div>
    </header>

    <div ref="host" class="chart" />

    <div class="legend">
      <template v-if="store.colorBy === 'macroarea'">
        <span v-for="(m, i) in MACRO_AREAS" :key="m" class="item">
          <i :style="{ background: PALETTE[i] }" />{{ m }}
        </span>
      </template>
      <template v-else>
        <span class="item"><i :style="{ background: C.positive }" />十年增长</span>
        <span class="item"><i :style="{ background: C.negative }" />十年衰退</span>
        <span class="item"><i :style="{ background: C.neutral }" />基线不可信</span>
      </template>
      <span class="item note"><i class="ring" />点越大 = 当月浏览量越高</span>
    </div>
  </section>
</template>

<style scoped>
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  display: flex; flex-direction: column;
  min-height: 0; height: 100%;
}
header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: var(--sp-3); margin-bottom: var(--sp-2);
}
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 0; font-size: var(--fs-small); color: var(--text-muted); }
.chart { flex: 1; min-height: 400px; }

.ctrls { display: flex; align-items: center; gap: var(--sp-3); flex: none; }
.seg { display: flex; border: 1px solid var(--border); border-radius: var(--radius-pill); overflow: hidden; }
.seg button {
  border: 0; background: transparent; cursor: pointer;
  padding: 4px 13px; font-size: var(--fs-small); color: var(--text-secondary);
  font-family: inherit; white-space: nowrap;
  transition: background var(--dur-fast) var(--ease-out);
}
.seg button:hover { background: var(--bg-subtle); }
.seg button.on { background: var(--accent); color: var(--text-inverse); }
.chk { display: flex; align-items: center; gap: 5px; font-size: var(--fs-small); color: var(--text-secondary); cursor: pointer; }
.chk input { accent-color: var(--accent); }

.legend {
  display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-4);
  padding-top: var(--sp-2); margin-top: var(--sp-1);
  border-top: 1px solid var(--border);
  font-size: var(--fs-micro); color: var(--text-secondary);
}
.legend .item { display: inline-flex; align-items: center; gap: 5px; }
.legend i { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.legend .note { color: var(--text-muted); margin-left: auto; }
.legend .ring { background: transparent; border: 1.5px solid var(--text-muted); }
</style>
