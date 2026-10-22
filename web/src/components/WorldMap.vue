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
import { MACRO_AREAS } from '@/types'
import { categoryPalette, semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const { macro: macroLabel, language: langLabel } = useDisplayNames()
const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)
/**
 * 当前地图缩放倍数（由 georoam 事件回读）。
 * 只用来决定"远景聚合 / 近景逐点"，所以不需要很精确。
 */
const mapZoom = ref(1.15)
/** georoam 防抖计时器：等手势停下再切"聚合/逐点"，避免在动画中间态重绘 */
let roamTimer = 0

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
    distSubAgg: '每块 = 该区域的语言数，块越大语言越多 · 放大可见单个语言',
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
    langsUnit: '门语言',
    zoomHint: '放大可见单个语言',
    aggMode: '远景：点已按经纬网聚合成密度块（每块 = 该区域的语言数）',
    dotMode: '近景：一个点一门语言，可逐一点选',
    lowBase: '基线过低，趋势不可信',
  },
  en: {
    distTitle: 'World language distribution',
    distSub: 'each dot is a language · coloured by area',
    distSubAgg: 'each block = the language count of that area; bigger = more · zoom in for individual dots',
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
    langsUnit: 'languages',
    zoomHint: 'zoom in to see individual languages',
    aggMode: 'Far view: dots are binned into a grid, one block per area (block = language count)',
    dotMode: 'Near view: one dot per language, individually selectable',
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
 *
 * 还有一个体验问题：2,652 个彩色小点铺满地图，看起来像一层"彩纸屑"，
 * 密到让人不适。实测按经纬网聚合最多也只能从 2,652 降到约 1,000 ——
 * **数量不是主因，主因是大量离散的彩色小点**。
 *
 * 所以做成**按缩放分级**：
 *   远景（zoom < AGG_ZOOM）→ 聚合成经纬网格，每格一个较软的大色块，按格内语言数放大；
 *                            颜色仍按语区，但透明度低，叠在一起形成"密度场"而不是散点
 *   近景（zoom ≥ AGG_ZOOM）→ 切成单个语言的点，可逐一点选
 * 切换阈值取 2.0×：默认视野 1.15× 看密度，放大一下就进入个体视图。
 */
const AGG_ZOOM = 2.0
/** 聚合时的经纬网格边长（度）。2.5° 下大约 1,079 格 */
const AGG_CELL = 2.5

const contextData = computed(() => {
  const matched = store.matchedIds
  const filtering = store.hasFilter
  const rows = store.langs
    .filter((l) => l.latitude && l.longitude && keepLang(l.wals_id))

  // ---------- 近景：一个语言一个点 ----------
  if (mapZoom.value >= AGG_ZOOM) {
    return rows.map((l) => {
      const hit = !filtering || matched.has(l.wals_id)
      const isSel = store.selected === l.wals_id
      return {
        name: l.name, display: langLabel(l), wals_id: l.wals_id,
        value: [l.longitude, l.latitude, isSel ? 1 : 0, filtering && hit ? 1 : 0],
        family: l.family || '—', macroarea: l.macroarea,
        itemStyle: {
          color: store.colorBy === 'trend' ? C.textMuted : baseColor(l),
          opacity: isSel ? 1 : hit ? (filtering ? 1 : 0.5) : 0.05,
          borderColor: (isSel || (filtering && hit)) ? C.surface : 'transparent',
          borderWidth: isSel ? 2.5 : (filtering && hit) ? 1.2 : 0,
        },
      }
    })
  }

  // ---------- 远景：按经纬网聚合 ----------
  const cells = new Map<string, {
    lngSum: number; latSum: number; n: number; hit: boolean
    sel: boolean; areas: Map<string, number>; names: string[]
  }>()
  for (const l of rows) {
    const lng = Number(l.longitude)
    const lat = Number(l.latitude)
    const key = `${Math.floor(lng / AGG_CELL)}|${Math.floor(lat / AGG_CELL)}`
    const hit = !filtering || matched.has(l.wals_id)
    const isSel = store.selected === l.wals_id
    let cell = cells.get(key)
    if (!cell) {
      cell = { lngSum: 0, latSum: 0, n: 0, hit: false, sel: false, areas: new Map(), names: [] }
      cells.set(key, cell)
    }
    cell.lngSum += lng
    cell.latSum += lat
    cell.n += 1
    cell.hit = cell.hit || hit
    cell.sel = cell.sel || isSel
    const area = l.macroarea ?? '—'
    cell.areas.set(area, (cell.areas.get(area) ?? 0) + 1)
    if (cell.names.length < 8) cell.names.push(langLabel(l))
  }

  return [...cells.values()].map((c) => {
    // 颜色取格内最多的语区，保留编码又不至于变成彩纸屑
    let top = C.neutral
    let best = -1
    for (const [area, k] of c.areas) {
      if (k > best) {
        best = k
        top = macroColor.get(area) ?? C.neutral
      }
    }
    return {
      name: `${c.n}`,
      display: c.names.join(store.lang === 'zh' ? '、' : ', '),
      count: c.n,
      names: c.names,
      // 位置用格内语言的**质心**，不是"第一个语言的坐标"。
      // 用第一个的话块会偏向格子的一角，看着就像点和地图错位。
      value: [c.lngSum / c.n, c.latSum / c.n, c.sel ? 1 : 0, c.hit ? 1 : 0, c.n],
      macroarea: [...c.areas.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null,
      itemStyle: {
        color: store.colorBy === 'trend' ? C.textMuted : top,
        // 低透明度 + 按数量放大 = 叠成密度场，而不是一颗颗散点
        opacity: c.sel ? 0.95 : !c.hit ? 0.05 : filtering ? 0.5 : 0.17,
        borderColor: c.sel ? C.accent : 'transparent',
        borderWidth: c.sel ? 2 : 0,
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
  const d: any = inVit
    ?? contextData.value.find((x: any) => x.wals_id === sel)
    // 远景聚合模式下，单个语言没有自己的点了 —— 退而求其次，
    // 找到"包含它的那个聚合块"（建格子时给含选中语言的格子打了 sel 标记）。
    ?? contextData.value.find((x: any) => Array.isArray(x.value) && x.value[2] === 1)
  if (!d) return []
  // 半径与点当前大小成正比，环才不会忽大忽小。
  // effectScatter 的涟漪会在此基础上再放大 scale 倍。
  const dot = inVit
    ? sizeOf(d.value)
    : d.count != null
      ? Math.min(6 + Math.sqrt(d.count) * 5.5, 30)   // 聚合格：与 symbolSize 保持一致
      : (d.value?.[2] ? 11 : 3.4)
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
    // ⚠️ 必须关掉更新动画。主题里 animationDurationUpdate = 480ms，
    // 而远景(聚合块) 与近景(逐点) 的坐标完全不同 —— 开着动画时切换模式，
    // 新点会从旧坐标**飞**到新坐标，看起来就是"点跟地图错位"。
    animation: false,
    // value 长度 > 4 说明是聚合格（val[4] = 格内语言数），否则是单个语言。
    // 聚合格按数量放大：大的更"重"，叠起来像密度场而不是均匀的散点。
    symbolSize: (val: number[]) => (val.length > 4
      ? Math.min(6 + Math.sqrt(val[4]) * 5.5, 30)
      : (val[2] ? 11 : 3.4) * (val[3] ? 1.5 : 1)),
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
      // 远景聚合块：这里代表的是"N 门语言"，不是单个语言
      if (d.count != null) {
        return `<strong>${d.count} ${t.value.langsUnit}</strong><br>` +
          `<span style="color:${C.textSecondary}">${nm}</span><br>` +
          `<em style="color:${C.textMuted}">${t.value.zoomHint}</em>`
      }
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
  : { t: t.value.distTitle, s: isAgg.value ? t.value.distSubAgg : t.value.distSub }
)

/** 当前是"远景聚合"还是"近景逐点"——值得写在副标题里，否则用户不知道点变了形 */
const isAgg = computed(() => mapZoom.value < AGG_ZOOM)

// 跟随**容器**尺寸变化（侧栏折叠、切换选项卡时窗口尺寸并不变，
// 只监听 window.resize 会导致画布保持旧宽度、压住相邻区域）
const { schedule: scheduleResize } = useChartResize(host, chart)

onMounted(async () => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  chart.value.on('click', (p: any) => {
    if (p.data?.wals_id) store.select(p.data.wals_id)
  })
  // 缩放跨越阈值时要在"聚合"与"逐点"之间切换。
  //
  // 三个关键点（都是踩出来的）：
  //  · **等手势停下来再切**（250ms 防抖）。缩放动画途中 setOption，
  //    ECharts 拿到的 geo 变换可能还是中间态，投影就跟地图对不上。
  //  · **只在跨越阈值时**才改 mapZoom —— 它每帧都变的话 contextData 会每帧重算
  //    并触发整条 series 重绘，缩放会卡。
  //  · 重绘走 contextData 的 watcher（合并渲染）。不能用 render(true)：
  //    那会重建 geo 组件、把用户刚拖好的缩放重置掉，于是又触发 georoam，来回抖动。
  //  · 另外 ctx 系列的 animation 已关 —— 否则切换模式时新点会从旧坐标飞过来。
  chart.value.on('georoam', () => {
    clearTimeout(roamTimer)
    roamTimer = window.setTimeout(() => {
      const z = Number(chart.value?.getOption?.()?.geo?.[0]?.zoom ?? mapZoom.value)
      const wasAgg = mapZoom.value < AGG_ZOOM
      const isAgg = z < AGG_ZOOM
      if (wasAgg !== isAgg) mapZoom.value = z
    }, 250)
  })
  await ensureWorld()
  render(true)
  // 首次渲染后再对一次尺寸：挂载瞬间容器可能还没完成布局
  scheduleResize()
  window.addEventListener('resize', scheduleResize)
})

onBeforeUnmount(() => {
  clearTimeout(roamTimer)
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
      <span class="item mode">{{ isAgg ? t.aggMode : t.dotMode }}</span>
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
/* 当前渲染模式的说明（远景聚合 / 近景逐点） */
.legend .mode { color: var(--text-muted); margin-left: auto; }
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
