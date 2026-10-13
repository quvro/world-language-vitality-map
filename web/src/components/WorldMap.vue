<script setup lang="ts">
/**
 * 世界语言地图。
 *
 * 两个图层始终共存：
 *   context  全部有坐标的语言，小点。负责「语言在哪里」。
 *   vitality 有维基版本的那一批。大小随时间轴变化，负责「谁在数字空间活着」。
 *
 * 三个坑（都已实测，别再踩）：
 *
 * 1. **大小不能用「当月浏览量 / 当月全局最大」**。
 *    德语维基月浏览约 7 亿，多数语言只有几千。开方压缩后几乎所有点都被挤在
 *    最小尺寸附近 —— 实测拖时间轴时尺寸中位变化只有 **0.05px**，0.3% 的变化
 *    肉眼可辨，看起来就是"点了没反应"。地图其实一直在更新，只是看不见。
 *    改用「相对该语言自身十年峰值」后中位变化 1.96px、59% 可辨。
 *
 * 2. **筛选不能把点从地图上删掉**。多选语区后点一下子变少会让人困惑
 *    （"选了反而少了"）。所以底图始终绘制全部语言，未命中的淡出作地理参照。
 *
 * 3. **快速缩放时点会与地图错位**。geo 漫游动画期间若出现渐进渲染，
 *    点会短暂画在旧位置。所以要设 scaleLimit 并关掉这两个系列的渐进渲染。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { COUNTRY_ZH } from '@/countries'
import { useChartResize } from '@/useChartResize'
import { MACRO_AREAS, type MacroArea } from '@/types'
import { categoryPalette, semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const { macro: macroLabel, language: langLabel } = useDisplayNames()
const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)

const e = () => (window as any).echarts
const C = semanticColors()
const PALETTE = categoryPalette()
const macroColor = new Map<string, string>(
  MACRO_AREAS.map((m, i) => [m, PALETTE[i]])
)

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

const T = {
  zh: {
    distTitle: '世界语言分布',
    distSub: '每个点是一门语言 · 按语区着色',
    vitTitle: '数字活力地图',
    vitSub: '大小 = 活跃程度 · 颜色 = 十年趋势',
    byMacro: '按语区',
    byTrend: '按趋势',
    vitalityLayer: '活力层',
    onlySelected: '只看选中',
    onlySelectedHint: '选中一门语言后，这里会只显示它',
    pickFirst: '先点一个点',
    sizeRel: '相对自身峰值',
    sizeAbs: '跨语言比较',
    month: '当前月份',
    legendRelative: '点越大 = 该语言当月浏览量越接近它自己的十年峰值',
    legendAbsolute: '点越大 = 当月浏览量在所有语言中排名越靠前',
    grown: '十年增长', shrunk: '十年衰退', unreliable: '基线不可信',
    highlight: (n: string) => `高亮 = 当前筛选命中的 ${n} 门语言（其余淡出保留作地理参照）`,
    noWiki: '没有维基百科版本，无时间序列', views: '浏览', trend: '十年趋势',
    lowBase: '基线过低，趋势不可信',
  },
  en: {
    distTitle: 'World language distribution',
    distSub: 'each dot is a language · coloured by area',
    vitTitle: 'Digital vitality',
    vitSub: 'size = current activity · colour = ten-year trend',
    byMacro: 'By area',
    byTrend: 'By trend',
    vitalityLayer: 'Vitality',
    onlySelected: 'Selected only',
    onlySelectedHint: 'Select a language first; this then shows only it',
    pickFirst: 'click a dot first',
    sizeRel: 'vs own peak',
    sizeAbs: 'across langs',
    month: 'Month',
    legendRelative: 'Bigger = this month’s views closer to that language’s own ten-year peak',
    legendAbsolute: 'Bigger = this month’s views ranked higher across all languages',
    grown: 'Grew', shrunk: 'Declined', unreliable: 'Weak baseline',
    highlight: (n: string) => `Highlighted = the ${n} languages matching the current filter (the rest fade but stay as context)`,
    noWiki: 'No Wikipedia edition, so no time series', views: 'views', trend: '10-yr trend',
    lowBase: 'baseline too low, trend unreliable',
  },
} as const

const t = computed(() => T[store.lang])

/** 当前月份的可读形式，例如 2017-06 */
const monthLabel = computed(() => {
  const m = store.currentMonth
  return m ? `${m.slice(0, 4)}-${m.slice(4, 6)}` : '—'
})

/**
 * 底图：**始终绘制全部语言**，只把未命中筛选的淡出。
 * 早期版本直接从 filtered 建底图，导致选一个语区后地图上的点骤减，看着像出了错。
 */
const contextData = computed(() => {
  const matched = store.matchedIds
  const filtering = store.hasFilter
  return store.langs
    .filter((l) => l.latitude && l.longitude && keepLang(l.wals_id))
    .map((l) => {
      const hit = !filtering || matched.has(l.wals_id)
      const isSel = store.selected === l.wals_id
      return {
        name: l.name, display: langLabel(l), wals_id: l.wals_id,
        value: [l.longitude, l.latitude, isSel ? 1 : 0, filtering && hit ? 1 : 0],
        family: l.family || '—', macroarea: l.macroarea,
        itemStyle: {
          color: store.colorBy === 'trend' ? C.textMuted : baseColor(l),
          // 「高亮」是对**筛选命中的全部语言**做的，不只对点选的那一个：
          //   命中 + 有筛选  → 完全不透明 + 白描边 + 略放大（见 symbolSize）
          //   命中 + 无筛选  → 常规
          //   未命中        → 近乎隐形，只留一层地理底影
          opacity: isSel ? 1 : hit ? (filtering ? 1 : 0.5) : 0.05,
          borderColor: (isSel || (filtering && hit)) ? C.surface : 'transparent',
          borderWidth: isSel ? 2.5 : (filtering && hit) ? 1.2 : 0,
        },
      }
    })
})

const trendColor = (g: number | null | undefined, ok?: boolean) =>
  !ok || g == null ? C.neutral : g >= 0 ? C.positive : C.negative

function baseColor(l: { macroarea: string | null; growth?: number; baseline_ok?: boolean }) {
  return store.colorBy === 'trend'
    ? trendColor(l.growth, l.baseline_ok)
    : (macroColor.get(l.macroarea ?? '') ?? C.neutral)
}

/**
 * 「只看选中」开关：选中后其余点全部不画。
 * 地图上 2600 多个点挤在一起时，靠放大+描边仍然很难找到刚点的那一个，
 * 所以给一个直接隐藏其余点的开关。对比集合里的语言同样保留。
 */
function keepLang(id: string): boolean {
  if (!store.hideUnselected || !store.selected) return true
  return id === store.selected || store.comparisonSet.includes(id)
}

const vitalityData = computed(() => {
  const views = store.currentViews
  const rank = store.currentRank
  const n = Math.max(Object.keys(views).length, 1)
  // 活力层也必须响应筛选 —— 否则加了活力层后，被筛掉的语言仍然亮着，
  // 「未命中淡出」的效果就看不见了
  const matched = store.matchedIds
  const filtering = store.hasFilter
  return store.withVitality
    .filter((l) => l.latitude && l.longitude && views[l.wals_id] != null
      && keepLang(l.wals_id))
    .slice()
    .sort((a, b) => (a.wals_id < b.wals_id ? -1 : 1))
    .map((l) => {
      const v = views[l.wals_id]
      const isSel = store.selected === l.wals_id
      const hit = !filtering || matched.has(l.wals_id)
      const dim = (store.selected && !isSel) || !hit
      const peak = store.ownPeak[l.wals_id] || 1
      // 排名分位（1 = 第一），供「跨语言比较」尺度使用
      const rankPct = 1 - (rank[l.wals_id] ?? n) / n
      return {
        name: l.name, display: langLabel(l), wals_id: l.wals_id,
        // 所有 symbolSize 需要的东西都编进 value，避免依赖回调的 params 参数
        //   [0]经度 [1]纬度 [2]当月浏览量 [3]是否选中 [4]自身十年峰值 [5]排名分位
        //   [6]是否命中筛选（命中要放大，见 sizeOf）
        value: [l.longitude, l.latitude, v, isSel ? 1 : 0, peak, rankPct,
          filtering && hit ? 1 : 0],
        views: v, growth: l.growth, baseline_ok: l.baseline_ok,
        macroarea: l.macroarea,
        itemStyle: {
          color: baseColor(l),
          // 与底图一致：命中筛选的全部语言都被高亮（不透明 + 白描边 + 放大），
          // 未命中的压到近乎隐形。选中点额外由 halo 系列加涟漪圈。
          borderColor: C.surface,
          borderWidth: isSel ? 2.5 : (filtering && hit) ? 1.2 : 1,
          opacity: !hit ? 0.05 : isSel ? 1 : filtering ? 1 : dim ? 0.1 : 0.72,
        },
      }
    })
})

/**
 * 大小映射。两种尺度都刻意让「相邻月份的差异足够大」：
 *   relative  相对自身十年峰值 —— 每个点沿自己的轨迹起伏，动画明显
 *   absolute  当月排名分位 —— 保留跨语言可比性，同时避免被德语维基压平
 * 只读 val，不依赖 ECharts 是否把 params 传给回调。
 */
function sizeOf(val: number[]): number {
  const isSel = !!val[3]
  let s: number
  if (store.sizeMode === 'relative') {
    const rel = Math.min(Number(val[2] ?? 0) / (Number(val[4]) || 1), 1)
    s = 4 + Math.sqrt(rel) * 24
  } else {
    s = 4 + Math.min(Math.max(Number(val[5] ?? 0), 0), 1) * 26
  }
  // 命中筛选的点整体放大，让"这一批"从底影里浮出来
  return (isSel ? s + 5 : s) * (val[6] ? 1.3 : 1)
}

/**
 * 选中点的高亮环。
 *
 * 为什么单独做一层：在密集点里，「加粗描边 + 放大几像素」根本不够醒目 ——
 * 描边色和点本身的填充色在同一个色系里，视觉上糊在一起。
 * 所以额外画一个**空心大圈**罩在选中点外面，形成靶心效果。
 */
const haloData = computed(() => {
  const sel = store.selected
  if (!sel) return []
  // 先在活力层找，找不到再退回底图 ——
  // 否则选到一门**没有维基版本**的语言时活力层里根本没有它，光环就不会出现。
  const inVit: any = store.showVitality
    ? vitalityData.value.find((x) => x.wals_id === sel)
    : undefined
  const d: any = inVit ?? contextData.value.find((x) => x.wals_id === sel)
  if (!d) return []
  // 半径与点当前大小成正比，环才不会忽大忽小。
  // effectScatter 的涟漪会在此基础上再放大 scale 倍。
  const dot = inVit ? sizeOf(d.value) : (d.value?.[2] ? 11 : 3.4)
  return [{
    name: d.display ?? d.name,
    wals_id: sel,
    value: d.value,
    symbolSize: dot + 6,
  }]
})

function buildSeries() {
  const ctx = {
    id: 'ctx', name: 'ctx', type: 'scatter', coordinateSystem: 'geo',
    data: contextData.value,
    z: 1,
    emphasis: { scale: 1.5 },
    // 关掉渐进渲染：geo 漫游时它会让点短暂画在旧位置（快速缩放"错位"的来源）
    progressive: 0,
    symbolSize: (val: number[]) => (val[2] ? 11 : 3.4) * (val[3] ? 1.5 : 1),
  }
  const vit = {
    id: 'vit', name: 'vit', type: 'scatter', coordinateSystem: 'geo',
    data: store.showVitality ? vitalityData.value : [],
    z: 2,
    emphasis: { scale: 1.2 },
    progressive: 0,
    symbolSize: (val: number[]) => sizeOf(val),
  }
  // 高亮环。用 effectScatter 而不是普通 scatter：
  // 静态描边在密集点里实测"画出来了但看不出来"（渲染验证确认过环存在于 SVG 中），
  // 而 effectScatter 会画**向外扩散的涟漪**，动态的东西才抓得住眼睛。
  // 同时保留静态描边，这样即使动画被系统设置关掉，环依然在。
  const halo = {
    id: 'halo', name: 'halo', type: 'effectScatter', coordinateSystem: 'geo',
    data: haloData.value,
    z: 5, silent: true, progressive: 0,
    showEffectOn: 'render',
    // ⚠️ rippleEffect.color 必须显式给。它默认取 itemStyle.color，
    // 而这里把 itemStyle.color 设成了 transparent（为了让静态符号只显示描边），
    // 于是涟漪也跟着透明 —— 表现就是"能看见一个静止的红圈，但它不扩散"。
    rippleEffect: { brushType: 'stroke', scale: 2.6, period: 3.2, color: C.accent },
    itemStyle: {
      color: 'transparent',
      borderColor: C.accent,
      borderWidth: 3,
      shadowBlur: 8,
      shadowColor: C.accent,
    },
  }
  return [ctx, vit, halo]
}

const OPT_BASE = {
  tooltip: {
    trigger: 'item',
    formatter: (p: any) => {
      // 悬停到国家区域（而不是语言点）
      if (p.componentType === 'geo') {
        const nm = store.lang === 'zh' ? (COUNTRY_ZH[p.name] ?? p.name) : p.name
        return `<span style="color:${C.textSecondary}">${nm}</span>`
      }
      const d = p.data
      if (!d) return ''
      const nm = d.display ?? d.name
      if (d.views == null) {
        return `<strong>${nm}</strong><br>` +
          `<span style="color:${C.textMuted}">${d.macroarea ?? '—'}</span><br>` +
          `<em style="color:${C.textMuted}">${t.value.noWiki}</em>`
      }
      const g = d.growth == null ? '—'
        : `${d.growth >= 0 ? '+' : ''}${(d.growth * 100).toFixed(1)}%`
      return `<strong>${nm}</strong><br>` +
        `<span style="color:${C.textMuted}">${monthLabel.value} ${t.value.views}</span> ` +
        `${Number(d.views).toLocaleString('en-US')}<br>` +
        `<span style="color:${C.textMuted}">${t.value.trend}</span> ${g}` +
        (d.baseline_ok ? '' : `<br><em style="color:${C.textMuted}">${t.value.lowBase}</em>`)
    },
  },
  // scaleLimit 限制缩放范围，避免缩到极端时点全部挤在一起
  geo: {
    map: 'world', roam: true, zoom: 1.15, center: [10, 18],
    scaleLimit: { min: 0.9, max: 14 },
    // 国家名的中英切换：world.js 的区域名是 Natural Earth 的缩写英文，没有 ISO 码，
    // 所以用 countries.ts 里手写的全量映射。
    nameMap: store.lang === 'zh' ? COUNTRY_ZH : {},
  },
}

function render(full = false) {
  if (!chart.value) return
  const series = buildSeries()
  if (full) chart.value.setOption({ ...OPT_BASE, series }, true)
  else chart.value.setOption({ series })
}

const title = computed(() => store.colorBy === 'trend'
  ? { t: t.value.vitTitle, s: t.value.vitSub }
  : { t: t.value.distTitle, s: t.value.distSub }
)

// 跟随**容器**尺寸变化（侧栏折叠、切换选项卡时窗口尺寸并不变，
// 只监听 window.resize 会导致画布保持旧宽度、压住相邻区域）
const { schedule: scheduleResize } = useChartResize(host, chart)

onMounted(async () => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  chart.value.on('click', (p: any) => {
    if (p.data?.wals_id) store.select(p.data.wals_id)
  })
  await ensureWorld()
  render(true)
  // 首次渲染后再对一次尺寸：挂载瞬间容器可能还没完成布局
  scheduleResize()
  window.addEventListener('resize', scheduleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', scheduleResize)
  chart.value?.dispose()
})

// ---------------------------------------------------------------- 重绘触发
//
// 这里踩过一个坑：原本是逐字段枚举 watcher（colorBy / showVitality / filtered /
// sizeMode / lang / monthIndex / selected）。后来给「只看选中」加了
// store.hideUnselected、也写进了 computed 的过滤，**却忘了加对应的 watcher** ——
// ECharts 是命令式渲染，状态变了没人调 render()，于是那个开关点了完全没反应。
//
// 改成**直接盯住要画的数据本身**：数据变了就一定重画，不可能再漏。
watch([contextData, vitalityData, haloData], () => render(false))
// 只影响「渲染时读取」而不进数据的选项（symbolSize 回调里读 sizeMode、
// series.data 是否为空由 showVitality 决定），必须单独盯。
watch(() => [store.showVitality, store.sizeMode], () => render(false))
// 语言会改变 geo.nameMap（国家名），需要整份 option 重建。
// 代价是会重置地图缩放/平移，但切换语言是低频操作，可以接受。
watch(() => store.lang, () => render(true))
</script>

<template>
  <section class="card">
    <header>
      <div class="tl">
        <h2>{{ title.t }}</h2>
        <p class="hint">
          {{ title.s }} ·
          <span class="sizetip">{{ store.sizeMode === 'relative' ? t.legendRelative : t.legendAbsolute }}</span>
        </p>
      </div>
      <div class="ctrls">
        <div class="seg">
          <button :class="{ on: store.colorBy === 'macroarea' }"
                  @click="store.colorBy = 'macroarea'">{{ t.byMacro }}</button>
          <button :class="{ on: store.colorBy === 'trend' }"
                  @click="store.colorBy = 'trend'">{{ t.byTrend }}</button>
        </div>
        <div class="seg">
          <button :class="{ on: store.sizeMode === 'relative' }"
                  @click="store.sizeMode = 'relative'">{{ t.sizeRel }}</button>
          <button :class="{ on: store.sizeMode === 'absolute' }"
                  @click="store.sizeMode = 'absolute'">{{ t.sizeAbs }}</button>
        </div>
        <label class="chk">
          <input v-model="store.showVitality" type="checkbox">
          <span>{{ t.vitalityLayer }}</span>
        </label>
        <!-- 不设 disabled：禁用会让用户以为按钮坏了（实测反馈过）。
             未选中时点了不会有视觉变化，旁边给出原因说明。 -->
        <label class="chk" :class="{ warn: !store.selected }"
               :title="store.selected ? t.onlySelected : t.onlySelectedHint">
          <input v-model="store.hideUnselected" type="checkbox">
          <span>{{ t.onlySelected }}</span>
          <em v-if="!store.selected" class="why">{{ t.pickFirst }}</em>
        </label>
      </div>
    </header>

    <div class="monthbar">
      <span class="lab">{{ t.month }}</span>
      <strong class="val num">{{ monthLabel }}</strong>
    </div>

    <div ref="host" class="chart" />

    <div class="legend">
      <template v-if="store.colorBy === 'macroarea'">
        <span v-for="(m, i) in MACRO_AREAS" :key="m" class="item">
          <i :style="{ background: PALETTE[i] }" />{{ macroLabel(m) }}
        </span>
      </template>
      <template v-else>
        <span class="item"><i :style="{ background: C.positive }" />{{ t.grown }}</span>
        <span class="item"><i :style="{ background: C.negative }" />{{ t.shrunk }}</span>
        <span class="item"><i :style="{ background: C.neutral }" />{{ t.unreliable }}</span>
      </template>
      <span v-if="store.hasFilter" class="item hl">
        <i class="ringdot" />{{ t.highlight(store.filtered.length.toLocaleString('en-US')) }}
      </span>
    </div>
  </section>
</template>

<style scoped>
.card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  display: flex; flex-direction: column;
  min-height: 0; height: 100%;
}
header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: var(--sp-3); margin-bottom: var(--sp-2);
}
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 0; font-size: var(--fs-small); color: var(--text-muted); line-height: 1.5; }

.ctrls { display: flex; align-items: center; gap: var(--sp-2); flex: none; flex-wrap: wrap; justify-content: flex-end; }
.seg { display: flex; border: 1px solid var(--border); border-radius: var(--radius-pill); overflow: hidden; }
.seg button {
  border: 0; background: transparent; cursor: pointer;
  padding: 4px 11px; font-size: var(--fs-micro); color: var(--text-secondary);
  font-family: inherit; white-space: nowrap;
  transition: background var(--dur-fast) var(--ease-out);
}
.seg button:hover { background: var(--bg-subtle); }
.seg button.on { background: var(--accent); color: var(--text-inverse); }
.chk { display: flex; align-items: center; gap: 4px; font-size: var(--fs-micro); color: var(--text-secondary); cursor: pointer; }
.chk input { accent-color: var(--accent); }

/* 当前月份单独一行，不塞进说明句里（那样读起来很别扭） */
.monthbar {
  display: flex; align-items: baseline; gap: var(--sp-2);
  padding: 4px 0 var(--sp-2);
}
.monthbar .lab { font-size: var(--fs-micro); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.monthbar .val { font-size: 0.95rem; color: var(--accent); }

/* min-height 必须给 0：之前写 380px，卡片高度受限时图表不肯收缩，
   于是图例被挤到地图上面压住它。让 flex 自己分配高度即可。 */
.chart { flex: 1; min-height: 0; }

.legend {
  flex: none;
  display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-3);
  padding-top: var(--sp-2); margin-top: var(--sp-2);
  border-top: 1px solid var(--border);
  font-size: var(--fs-micro); color: var(--text-secondary);
}
.legend .item { display: inline-flex; align-items: center; gap: 5px; }
.legend i { width: 8px; height: 8px; border-radius: 50%; flex: none; }
/* 高亮图例：一个"白边实心点"，与地图上命中点的画法一致 */
.legend .hl { color: var(--text-secondary); }
.legend .ringdot {
  width: 11px; height: 11px; border-radius: 50%;
  background: var(--accent); border: 1.5px solid var(--bg-surface);
  box-shadow: 0 0 0 1.5px var(--accent);
}

.sizetip { color: var(--text-secondary); }
.chk.warn { opacity: 0.75; }
.chk .why {
  font-style: normal; font-size: var(--fs-micro);
  color: var(--text-muted); margin-left: 2px;
}
</style>
