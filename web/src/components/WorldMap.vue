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
import { MACRO_AREAS, hasCoords } from '@/types'
import { categoryPalette, semanticColors } from '@/theme/echarts-theme.js'
import { convexHull, spansDateline } from '@/hull'

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
    clickDrill: '点一下钻进这一块，逐点挑选里面有哪些语言',
    clickPick: '点一下选中这门语言',
    aggMode: '远景：点已按经纬网聚合成密度块（每块 = 该区域的语言数）',
    dotMode: '近景：一个点一门语言，可逐一点选',
    densityBtn: '密度块',
    dotsBtn: '逐点',
    glyphBtn: '字形',
    chTitle: '字形部件',
    chHint: '关掉一个维度，看地图还剩多少信息',
    chRing: '外环颜色', dRing: '← 濒危等级',
    chArc: '环内扇形', dArc: '← 描写深度',
    chCore: '中心点', dCore: '← 有无维基版本',
    chSize: '字形大小', dSize: '← 当月浏览量',
    chTicks: '外围刻度', dTicks: '← 其他维基项目数',
    glyphSub: '一个符号 = 一门语言：环色=濒危 · 扇形=深度 · 实心=有维基 · 大小=浏览量',
    legRing: '环 = 濒危', legWedge: '扇形 = 描写深度',
    legCore: '实心 = 有维基', legTick: '刻度 = 项目数',
    famCaption: (f: string, n: number, w: number) =>
      `${f} 语系 · 图上 ${n} 门，其中 ${w} 门有维基版本`,
    famDateline: '该语系横跨 180° 经线，只画连线不画轮廓',
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
    clickDrill: 'click to drill into this block and pick a language',
    clickPick: 'click to select this language',
    aggMode: 'Far view: dots are binned into a grid, one block per area (block = language count)',
    dotMode: 'Near view: one dot per language, individually selectable',
    densityBtn: 'Density',
    dotsBtn: 'Dots',
    glyphBtn: 'Glyphs',
    chTitle: 'Glyph channels',
    chHint: 'switch a dimension off and see how much is left',
    chRing: 'Outer ring', dRing: '← endangerment',
    chArc: 'Inner wedge', dArc: '← description depth',
    chCore: 'Centre dot', dCore: '← has Wikipedia',
    chSize: 'Glyph size', dSize: '← monthly views',
    chTicks: 'Outer ticks', dTicks: '← other wiki projects',
    glyphSub: 'one symbol = one language · ring=endangerment · wedge=depth · filled=has Wikipedia · size=views',
    legRing: 'ring = endangerment', legWedge: 'wedge = depth',
    legCore: 'filled = has Wikipedia', legTick: 'ticks = projects',
    famCaption: (f: string, n: number, w: number) =>
      `${f} family · ${n} languages on the map, ${w} with a Wikipedia`,
    famDateline: 'this family crosses the 180° meridian, so only the lines are drawn',
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
 * 所以做成**两种渲染方式**，由图例上的开关切换：
 *   密度块 → 聚合成经纬网格，每格一个较软的大色块，按格内语言数放大；
 *            颜色仍按语区，但透明度低，叠在一起形成"密度场"而不是散点
 *   逐点   → 一个语言一个点，可逐一点选
 *
 * ⚠️ **不跟随缩放自动切换** —— 见 onMounted 里那段说明，这是踩出来的。
 */
/** 聚合时的经纬网格边长（度）。2.5° 下大约 1,079 格 */
const AGG_CELL = 2.5

const contextData = computed(() => {
  const matched = store.matchedIds
  const filtering = store.hasFilter
  const rows = store.langs
    .filter((l) => hasCoords(l) && keepLang(l.wals_id))

  // 字形模式下底图不由这个 computed 提供（见 glyphItems），避免和字形重复绘制
  if (store.mapMode === 'glyph') return []

  // ---------- 近景：一个语言一个点 ----------
  if (store.mapMode === 'dots') {
    return rows.map((l) => {
      const hit = !filtering || matched.has(l.wals_id)
      const isSel = store.selected === l.wals_id
      // 同语系的其它语言：描一圈浅强调色，让"连线那头的点"也认得出
      const inFam = !isSel && (famIds.value?.has(l.wals_id) ?? false)
      return {
        name: l.name, display: langLabel(l), wals_id: l.wals_id,
        value: [l.longitude, l.latitude, isSel ? 1 : 0, filtering && hit ? 1 : 0],
        family: l.family || '—', macroarea: l.macroarea,
        itemStyle: {
          color: store.colorBy === 'trend' ? C.textMuted : baseColor(l),
          opacity: isSel ? 1 : hit ? (filtering ? 1 : 0.5) : 0.05,
          borderColor: isSel
            ? C.surface
            : inFam
              ? withAlpha(C.accent, 0.85)
              : (filtering && hit) ? C.surface : 'transparent',
          borderWidth: isSel ? 2.5 : inFam ? 1.3 : (filtering && hit) ? 1.2 : 0,
        },
      }
    })
  }

  // ---------- 远景：按经纬网聚合 ----------
  const cells = new Map<string, {
    lngSum: number; latSum: number; n: number; hit: boolean
    sel: boolean; areas: Map<string, number>; names: string[]
    /** 格内唯一的语言（n === 1 时才有），用于直接选中 */
    single?: string
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
    cell.single = cell.n === 1 ? l.wals_id : undefined
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
      // 密度块是**合成**出来的：它代表 n 门语言，本身没有身份。
      // 所以点选逻辑不能靠 wals_id —— 见 onMounted 里的 click 处理：
      //   只有一门语言 → 直接选中；多门 → 钻进去（放大并切到逐点）
      single: c.single,
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

/** 把 #rrggbb + 透明度 变成 rgba()。强调色需要"浅"版本，直接调透明度最省事 */
function withAlpha(hex: string, a: number): string {
  const h = hex.replace('#', '')
  if (h.length < 6) return hex
  const r = parseInt(h.slice(0, 2), 16)
  const g = parseInt(h.slice(2, 4), 16)
  const b = parseInt(h.slice(4, 6), 16)
  return `rgba(${r},${g},${b},${a})`
}

/**
 * 选中语言所属语系的**其它成员**（不含它自己）。
 *
 * 定义在 contextData / vitalityData **之前** —— 两个图层都要读它，
 * 用来给"连线那头的点"加浅强调色。用过 computed 的先后顺序踩过坑。
 */
const famIds = computed<Set<string> | null>(() => {
  const sel = store.selected
  if (!sel) return null
  const self = store.langs.find((x) => x.wals_id === sel)
  const fam = self?.family
  if (!fam) return null
  const s = new Set<string>()
  for (const l of store.langs) {
    if (l.family === fam && l.wals_id !== sel) s.add(l.wals_id)
  }
  return s.size ? s : null
})

const vitalityData = computed(() => {
  const views = store.currentViews
  const rank = store.currentRank
  const n = Math.max(Object.keys(views).length, 1)
  // 活力层也必须响应筛选 —— 否则加了活力层后，被筛掉的语言仍然亮着，
  // 「未命中淡出」的效果就看不见了
  const matched = store.matchedIds
  const filtering = store.hasFilter
  return store.withVitality
    .filter((l) => hasCoords(l) && views[l.wals_id] != null
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
          // 同语系的其它语言：描边换成浅强调色，与底图的浅色底圈呼应。
          borderColor: !isSel && famIds.value?.has(l.wals_id)
            ? withAlpha(C.accent, 0.85)
            : C.surface,
          borderWidth: isSel ? 2.5 : (!isSel && famIds.value?.has(l.wals_id)) ? 1.4
            : (filtering && hit) ? 1.2 : 1,
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
 * 选中语言所属的**语系星群** —— 在地图上直接表达「从属关系」。
 *
 * 用户要的是「点大小以外的关系表达，比如语言从属关系网，而且想直接长在首页地图上」。
 * 但 254 个语系全画出来会立刻回到"太密"的老问题上，所以做成**按需显现**：
 *   平时地图保持干净的密度场；
 *   选中一门语言 → 画出它所在语系的全部成员之间的连线 + 语系轮廓 + 一行说明。
 *
 * 这样既回答了「这门语言和谁是一家」，又不在默认状态增加任何视觉负担。
 */
const selFamily = computed(() => {
  const sel = store.selected
  if (!sel) return null
  const self = store.langs.find((x) => x.wals_id === sel)
  const fam = self?.family
  if (!self || !fam) return null
  const members = store.langs.filter(
    (x) => x.family === fam && hasCoords(x))
  // 跨 180° 经线的语系（南岛语系就是，322 门）画不出单个多边形，
  // 只能画连线。这个事实要写进说明，否则用户会以为轮廓坏了。
  const dateline = spansDateline(
    members.map((m) => [Number(m.longitude), Number(m.latitude)]))
  return {
    family: fam,
    self,
    members,
    withWiki: members.filter((x) => x.wiki_code).length,
    dateline,
  }
})

/**
 * 连线那头的点：套一圈**浅强调色**。
 *
 * 用户要求「选中一门语言时，线链接的点也有一个比较浅的强调色」。
 * 做成单独一层而不是改点本身的填充色，是因为填充色承载编码
 * （语区 / 十年趋势），改掉就丢信息了；套一层浅色底圈既能强调、又不破坏编码。
 * z 卡在底图(1)与活力层(2)之间，会从点背后露出一圈光晕。
 */
const famGlow = computed(() => {
  const ids = famIds.value
  if (!ids) return []
  const out: any[] = []
  for (const l of store.langs) {
    if (!ids.has(l.wals_id)) continue
    if (!hasCoords(l)) continue
    if (!keepLang(l.wals_id)) continue
    out.push({
      name: l.name,
      value: [Number(l.longitude), Number(l.latitude)],
      wals_id: l.wals_id,
    })
  }
  // 抗拥挤的前提：重要/显眼的字形先占位（见下方 renderGlyph 的贪心抽稀）
  out.sort((a, b) => (b.r * b.opacity) - (a.r * a.opacity))
  return out
})

/** 同族连线：从选中语言放射到同语系的其它语言 */
const famStar = computed(() => {
  const f = selFamily.value
  if (!f || !hasCoords(f.self)) return []
  if (f.members.length < 2 || f.members.length > 500) return []
  const o: [number, number] = [Number(f.self.longitude), Number(f.self.latitude)]
  return f.members
    .filter((m) => m.wals_id !== f.self.wals_id)
    .map((m) => ({
      coords: [o, [Number(m.longitude), Number(m.latitude)] as [number, number]],
    }))
})

/** 语系轮廓（只有一个多边形，所以不会造成视觉噪音） */
const famHull = computed(() => {
  const f = selFamily.value
  if (!f || f.members.length < 3) return []
  const pts = f.members.map(
    (m) => [Number(m.longitude), Number(m.latitude)] as [number, number])
  // 跨 180° 经线的语系（如南岛语系）跳过：那样算出的外轮廓会横跨整个地图
  if (spansDateline(pts)) return []
  const hull = convexHull(pts)
  if (hull.length < 3) return []
  return [{ coords: [...hull, hull[0]] }]
})

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
  // 连线那头的点：浅强调色底圈（z 在底图与活力层之间，从点背后露出光晕）
  const famGlowSeries = {
    id: 'famglow', name: 'famglow', type: 'scatter', coordinateSystem: 'geo',
    data: famGlow.value,
    z: 1.5, silent: true, progressive: 0, animation: false,
    symbolSize: 11,
    itemStyle: {
      color: withAlpha(C.accent, 0.16),
      borderColor: withAlpha(C.accent, 0.42),
      borderWidth: 1,
    },
  }
  // 语系星群：只画在"选中语言所属的那一个语系"上（z 在点之下、地图之上）
  const famHullSeries = {
    id: 'famhull', name: 'famhull', type: 'lines', coordinateSystem: 'geo',
    data: famHull.value,
    z: 0.6, silent: true,
    polyline: true,
    lineStyle: { color: C.accent, width: 1.2, opacity: 0.55 },
    // lines 不支持填充，所以只用轮廓表达范围 —— 也刚好更轻
    effect: { show: false },
  }
  const famStarSeries = {
    id: 'famstar', name: 'famstar', type: 'lines', coordinateSystem: 'geo',
    data: famStar.value,
    z: 0.7, silent: true,
    lineStyle: { color: C.accent, width: 0.8, opacity: 0.35, curveness: 0.12 },
    effect: { show: false },
  }
  // 复合字形层。因为要接 tooltip 与点击，所以不是 silent；
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
  return [famHullSeries, famStarSeries, famGlowSeries, ctx, glyphSeries, vit, halo]
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
          `<em style="color:${C.textMuted}">${d.count === 1 ? t.value.clickPick : t.value.clickDrill}</em>`
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

const title = computed(() => store.mapMode === 'glyph'
  ? { t: t.value.distTitle, s: t.value.glyphSub }
  : store.colorBy === 'trend'
  ? { t: t.value.vitTitle, s: t.value.vitSub }
  : { t: t.value.distTitle, s: isAgg.value ? t.value.distSubAgg : t.value.distSub }
)

/** 当前是"远景聚合"还是"近景逐点"——值得写在副标题里，否则用户不知道点变了形 */

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
/**
 * 抗拥挤用的屏幕空间占位表。
 * 每个字形以屏幕坐标落格（26px），插入前检查 3×3 邻域里已放置的字形，
 * 只要与其中一个的距离小于两者半径和的 0.82 倍，就认为它放不下。
 * 用屏幕坐标而不是经纬度：缩放后字距自然拉开，抽稀随之放松，
 * 不必监听 roam，也就避开了「重绘与漫游动画打架」那个老问题。
 */
const GLYPH_CELL = 26
const glyphOcc = new Map<string, { x: number; y: number; r: number }[]>()

function glyphCellKey(x: number, y: number) {
  return Math.floor(x / GLYPH_CELL) + ',' + Math.floor(y / GLYPH_CELL)
}

function glyphCrowded(x: number, y: number, r: number) {
  const bx = Math.floor(x / GLYPH_CELL)
  const by = Math.floor(y / GLYPH_CELL)
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      const bucket = glyphOcc.get(bx + dx + ',' + (by + dy))
      if (!bucket) continue
      for (const o of bucket) {
        if (Math.hypot(o.x - x, o.y - y) < (o.r + r) * 0.82) return true
      }
    }
  }
  return false
}

function renderGlyph(params: any, api: any) {
  const it = glyphItems.value[params.dataIndex]
  if (!it) return null
  const pt = api.coord([it.lng, it.lat])
  if (!pt || !Number.isFinite(pt[0]) || !Number.isFinite(pt[1])) return null
  const x = pt[0]
  const y = pt[1]
  const r = it.r

  // 每轮绘制 ECharts 都从 dataIndex 0 开始 —— 用它重置占位表
  if (params.dataIndex === 0) glyphOcc.clear()
  // 选中的那门永远画出来，否则点一个小语种可能"点了没反应"
  const pinned = store.selected === it.wals_id
  if (!pinned && glyphCrowded(x, y, r)) {
    return { type: 'group', children: [] }
  }
  {
    const key = glyphCellKey(x, y)
    let bucket = glyphOcc.get(key)
    if (!bucket) glyphOcc.set(key, bucket = [])
    bucket.push({ x, y, r })
  }

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

/** 开着几个通道 —— 收起时也能一眼看到 */
const enabledChannels = computed(
  () => Object.values(store.glyphChannels).filter(Boolean).length)

function toggleChannel(key: keyof typeof store.glyphChannels, e: Event) {
  const on = (e.target as HTMLInputElement).checked
  store.glyphChannels[key] = on
}

const isAgg = computed(() => store.mapMode === 'density')

// 跟随**容器**尺寸变化（侧栏折叠、切换选项卡时窗口尺寸并不变，
// 只监听 window.resize 会导致画布保持旧宽度、压住相邻区域）
const { schedule: scheduleResize } = useChartResize(host, chart)

onMounted(async () => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  chart.value.on('click', (p: any) => {
    const d: any = p.data
    if (d?.wals_id) {
      store.select(d.wals_id)
      return
    }
    // 密度块是合成出来的，本身没有 wals_id —— 于是密度模式下
    // 2,385 门没有维基版本的语言原本**完全点不到**（用户发现的缺陷）。
    // 按块内语言数分流：
    //   只有一门 → 直接选中它
    //   多门     → 钻进这一块：放大到它并切到逐点，由用户自己挑
    if (d?.count == null) return
    if (d.single) {
      store.select(d.single)
      return
    }
    const [lng, lat] = Array.isArray(d.value) ? d.value : []
    if (Number.isFinite(lng) && Number.isFinite(lat)) {
      // 先改 geo（一次 setOption），再改 mapMode ——
      // 后者会触发 watcher 的合并渲染，那条路径只传 series，不会重置缩放。
      chart.value?.setOption({ geo: { center: [lng, lat], zoom: 6 } })
      store.mapMode = 'dots'
    }
  })
  // 这里**刻意不监听 georoam**。
  //
  // 之前"缩放跨过阈值就切换聚合/逐点"的做法，需要在漫游过程中 setOption，
  // 而它会打断 geo 的缩放补间，让渲染出的地图与模型里的 zoom/center 不一致 ——
  // 表现就是「缩放时地图错误移动，随便点一下数据点又复位」。
  // 用 isFinished() 等动画结束只能压住慢速缩放，**快速缩放**时跨阈值会来回触发，
  // 仍会撞在补间中间。
  //
  // 所以把这条路径整个去掉：缩放期间一次 setOption 都不发生，
  // 密度块 / 逐点只由用户点图例上的开关决定（store.mapMode）。
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
watch([contextData, vitalityData, haloData, famStar, famHull, famGlow, glyphItems],
  () => render(false))
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
        <!-- 头部压缩成一行：尺寸说明挪进 title 提示，把高度让给地图 -->
        <p class="hint" :title="store.sizeMode === 'relative' ? t.legendRelative : t.legendAbsolute">
          {{ title.s }}
        </p>
      </div>
    </header>

    <div class="monthbar">
      <span class="lab">{{ t.month }}</span>
      <strong class="val num">{{ monthLabel }}</strong>
    </div>

    <div ref="host" class="chart" />

    <!-- 字形通道开关：浮在地图左上角，只在字形模式下出现 -->
    <div v-if="store.mapMode === 'glyph'" class="channels"
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
    </div>

    <div class="legend">
      <template v-if="store.mapMode === 'glyph'">
        <span class="item gly"><i class="ring" />{{ t.legRing }}</span>
        <span class="item gly"><i class="wedge" />{{ t.legWedge }}</span>
        <span class="item gly"><i class="core" />{{ t.legCore }}</span>
        <span class="item gly"><i class="tick" />{{ t.legTick }}</span>
      </template>
      <template v-else-if="store.colorBy === 'macroarea'">
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
      <span v-if="selFamily" class="item fam">
        <i class="famdot" />{{ t.famCaption(selFamily.family, selFamily.members.length, selFamily.withWiki) }}
        <em v-if="selFamily.dateline" class="dl">{{ t.famDateline }}</em>
      </span>
      <span class="item mode">
        <button class="seg" :class="{ on: isAgg }" @click="store.mapMode = 'density'">{{ t.densityBtn }}</button>
        <button class="seg" :class="{ on: store.mapMode === 'dots' }" @click="store.mapMode = 'dots'">{{ t.dotsBtn }}</button>
        <button class="seg" :class="{ on: store.mapMode === 'glyph' }" @click="store.mapMode = 'glyph'">{{ t.glyphBtn }}</button>
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
/* 当前渲染模式的分段开关（密度块 / 逐点） */
.legend .mode { color: var(--text-muted); margin-left: auto; display: flex; gap: 2px; }
.legend .seg {
  border: 1px solid var(--border); background: var(--bg-surface);
  color: var(--text-secondary); font-family: inherit; font-size: var(--fs-micro);
  padding: 1px 8px; cursor: pointer; transition: background var(--dur-fast) var(--ease-out);
}
.legend .seg:first-child { border-radius: var(--radius-pill) 0 0 var(--radius-pill); }
.legend .seg:last-child { border-radius: 0 var(--radius-pill) var(--radius-pill) 0; border-left: 0; }
.legend .seg.on { background: var(--accent); border-color: var(--accent); color: var(--text-inverse); }

/* ---- 字形图例 ---- */
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

/* ---- 字形通道开关 ---- */
.card { position: relative; }
.channels {
  position: absolute; left: 16px; bottom: 56px; width: 268px; z-index: 6;
  background: rgba(255, 255, 255, 0.98);
  /* 用户反馈"太不明显"：改成强调色描边 + 左侧粗条 + 更重的投影，
     让它在地图上是一个明确的浮层，而不是一块半透明的白 */
  border: 1.5px solid var(--accent);
  border-left-width: 5px;
  border-radius: var(--radius-md);
  box-shadow: 0 10px 30px rgba(35, 32, 28, 0.17),
    0 0 0 5px rgba(228, 87, 46, 0.06);
  padding: 12px 13px 13px;
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
.channels.folded .ch-body { display: none; }
.ch-head {
  margin: 0 0 9px; font-size: var(--fs-micro); font-weight: 400;
  color: var(--text-muted); line-height: 1.5;
}
.ch-head span { display: block; font-weight: 400; color: var(--text-muted); }
.ch {
  display: flex; align-items: flex-start; gap: 7px;
  padding: 3px 0; cursor: pointer; user-select: none;
}
.ch input { position: absolute; opacity: 0; width: 0; height: 0; }
.ch-box {
  flex: none; width: 15px; height: 15px; margin-top: 2px;
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
.ch-txt b { font-size: var(--fs-small); font-weight: 600; color: var(--text-primary); }
.ch-txt i {
  font-style: normal; font-size: 10px; color: var(--text-muted);
}
/* 选中语言时显示的「语系星群」说明 */
.legend .fam { color: var(--text-secondary); display: inline-flex; align-items: center; gap: 5px; }
.legend .famdot {
  width: 7px; height: 7px; border-radius: 50%;
  border: 1.5px solid var(--accent); display: inline-block;
}
.legend .dl { font-style: normal; color: var(--text-muted); }
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
