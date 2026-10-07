<script setup lang="ts">
/**
 * 世界语言地图。
 *
 * 这里有两个「图层」，且**两个图层始终存在** —— 这是为了让地图与时间轴真正配合：
 *   底图 context  : 全部有坐标的语言，小点、按语区着色。永不消失。
 *   活力 vitality : 有维基版本的那一批，大小 = 当月浏览量，颜色 = 十年趋势。
 *
 * 之前的做法是「分布/活力」两个模式各自换掉整个数据集，结果切到活力模式时
 * 2,652 个点只剩 244 个、地图一下变空；而分布模式下拖时间轴又毫无反应。
 * 现在改成图层叠加：拖时间轴时底图不动、活力层平滑呼吸，两者始终同框。
 *
 * 动画：两个 series 的数量与数据顺序保持稳定，用 merge 方式 setOption，
 * 让 ECharts 能对 symbolSize 做补间 —— 这是「点会跟着时间轴长缩」的关键。
 * 早期用 setOption(opt, true)（notMerge）会把上一帧状态丢掉，动画就没了。
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
const macroColor = new Map(MACRO_AREAS.map((m, i) => [m, PALETTE[i]]))

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

/** 底图点位：只随筛选变化，不随时间变化 —— 所以拖时间轴时它不会抖。 */
const contextPoints = computed(() =>
  store.filtered
    .filter((l) => l.latitude && l.longitude)
    .map((l) => {
      const isSel = store.selected === l.wals_id
      const dim = store.selected && !isSel
      return {
        name: l.name,
        wals_id: l.wals_id,
        value: [l.longitude, l.latitude] as [number, number],
        family: l.family || '—',
        macroarea: l.macroarea,
        isSel,
        itemStyle: {
          color: macroColor.get(l.macroarea as MacroArea) ?? C.neutral,
          opacity: dim ? 0.18 : 0.5,
        },
        symbolSize: isSel ? 11 : 3.6,
      }
    })
)

/** 活力层点位：顺序稳定（按 wals_id 排序），这样 size 变化才能补间。 */
const vitalityPoints = computed(() => {
  const views = store.currentViews
  const max = Math.max(store.currentMax, 1)
  return store.withVitality
    .filter((l) => l.latitude && l.longitude && views[l.wals_id] != null)
    .slice()
    .sort((a, b) => (a.wals_id < b.wals_id ? -1 : 1))
    .map((l) => {
      const v = views[l.wals_id]
      const g = l.baseline_ok ? (l.growth ?? 0) : null
      const isSel = store.selected === l.wals_id
      const dim = store.selected && !isSel
      // 平方根压缩动态范围，否则大语种会把小语种压成一个像素
      const size = 5 + Math.sqrt(v / max) * 34
      return {
        name: l.name,
        wals_id: l.wals_id,
        value: [l.longitude, l.latitude] as [number, number],
        views: v,
        growth: l.growth,
        baseline_ok: l.baseline_ok,
        itemStyle: {
          color: g == null ? C.neutral : g >= 0 ? C.positive : C.negative,
          borderColor: isSel ? C.textPrimary : C.surface,
          borderWidth: isSel ? 2 : 1,
          opacity: dim ? 0.12 : 0.66,
        },
        symbolSize: isSel ? size + 5 : size,
        z: isSel ? 10 : 2,
      }
    })
})

function tooltipFormatter(p: any) {
  const d = p.data
  if (!d) return ''
  if (d.views == null) {
    return `<strong>${d.name}</strong><br>` +
      `<span style="color:${C.textMuted}">语系</span> ${d.family}<br>` +
      `<span style="color:${C.textMuted}">语区</span> ${d.macroarea}<br>` +
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

const BASE = {
  tooltip: { trigger: 'item', formatter: tooltipFormatter },
  geo: { map: 'world', roam: true, zoom: 1.15, center: [10, 18] },
}

function render(full = false) {
  if (!chart.value) return
  const opt = {
    ...BASE,
    series: [
      {
        id: 'ctx', name: '全部语言', type: 'scatter', coordinateSystem: 'geo',
        data: contextPoints.value, z: 1, emphasis: { scale: 1.6 },
      },
      {
        id: 'vit', name: '数字活力', type: 'scatter', coordinateSystem: 'geo',
        // 分布模式下活力层留空，但 series 本身仍在 —— 保持 series 数量稳定
        data: store.mapMode === 'vitality' ? vitalityPoints.value : [],
        z: 2, emphasis: { scale: 1.3 },
      },
    ],
  }
  // full=true 用于筛选/模式等结构性变化；时间轴变化走 merge 以便补间
  if (full) chart.value.setOption(opt, true)
  else chart.value.setOption({ series: opt.series })
}

const title = computed(() => store.mapMode === 'distribution'
  ? { t: '世界语言分布', s: `全部 ${contextPoints.value.length.toLocaleString('en-US')} 门有坐标的语言 · 按语区着色` }
  : { t: '数字活力地图', s: `点的大小 = ${store.currentMonth} 的浏览量 · 颜色 = 十年趋势 · 灰色底点为无维基版本的语言` }
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

// 结构性变化（筛选 / 模式）→ 整幅重绘
watch(
  () => [store.mapMode, store.filtered],
  () => render(true)
)
// 时间轴或选中变化 → merge 更新，让点的大小与描边平滑补间
watch(
  () => [store.monthIndex, store.selected],
  () => render(false)
)
</script>

<template>
  <section class="card">
    <header>
      <div>
        <h2>{{ title.t }}</h2>
        <p class="hint">{{ title.s }}</p>
      </div>
      <div class="seg">
        <button
          :class="{ on: store.mapMode === 'distribution' }"
          @click="store.mapMode = 'distribution'"
        >语区分布</button>
        <button
          :class="{ on: store.mapMode === 'vitality' }"
          @click="store.mapMode = 'vitality'"
        >数字活力</button>
      </div>
    </header>

    <div ref="host" class="chart" />

    <!-- 手写图例：比 ECharts 默认图例更贴主题，也避免两套色标混在一起 -->
    <div class="legend">
      <template v-if="store.mapMode === 'distribution'">
        <span v-for="(m, i) in MACRO_AREAS" :key="m" class="item">
          <i :style="{ background: PALETTE[i] }" />{{ m }}
        </span>
      </template>
      <template v-else>
        <span class="item"><i :style="{ background: C.positive }" />十年增长</span>
        <span class="item"><i :style="{ background: C.negative }" />十年衰退</span>
        <span class="item"><i :style="{ background: C.neutral }" />基线不可信</span>
        <span class="item note">
          <i class="ring" />点的大小 = 当月浏览量
        </span>
      </template>
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

.seg { display: flex; border: 1px solid var(--border); border-radius: var(--radius-pill); overflow: hidden; flex: none; }
.seg button {
  border: 0; background: transparent; cursor: pointer;
  padding: 4px 13px; font-size: var(--fs-small); color: var(--text-secondary);
  font-family: inherit; white-space: nowrap;
  transition: background var(--dur-fast) var(--ease-out);
}
.seg button:hover { background: var(--bg-subtle); }
.seg button.on { background: var(--accent); color: var(--text-inverse); }

.legend {
  display: flex; flex-wrap: wrap; gap: var(--sp-3) var(--sp-4);
  padding-top: var(--sp-2); margin-top: var(--sp-1);
  border-top: 1px solid var(--border);
  font-size: var(--fs-micro); color: var(--text-secondary);
}
.legend .item { display: inline-flex; align-items: center; gap: 5px; }
.legend i { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.legend .note { color: var(--text-muted); }
.legend .ring { background: transparent; border: 1.5px solid var(--text-muted); }
</style>
