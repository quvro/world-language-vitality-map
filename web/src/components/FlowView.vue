<script setup lang="ts">
/**
 * 流向图（桑基）—— 方案 C。
 *
 * 这张图要回答的问题只有一个，但它是整个项目最"会讲"的一句：
 *   **哪些语系的语言，正在流向"没有数字入口"那一端？**
 *
 * 三列：
 *   语系（前 N 个 + 其他） → 濒危等级（AES 1..6） → 有无维基百科版本
 * 流带宽度 = 语言数量。所以"宽阔的流"就是问题所在。
 *
 * 为什么不用力导向网络：2,662 个节点 + 边会变成一片毛球，
 * 与用户已经提过的"点太密"是同一类问题。桑基的信息密度高得多，
 * 而且它表达的是**流向**（流失），这是当前所有视图都缺的。
 *
 * 语系过多（实测约 250 个）会碎成细丝，所以只保留前 N 个，
 * 其余合并成「其他语系」——并在图例里写明合并了多少个、多少门语言。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { categoryPalette, semanticColors } from '@/theme/echarts-theme.js'
import { useChartResize } from '@/useChartResize'

const store = useDataset()
const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)
const C = semanticColors()
const PALETTE = categoryPalette()

/** 保留多少个语系，其余合并。太多会碎成细丝，太少看不出差异 */
const TOP_N = 14

const T = {
  zh: {
    title: '语言正在流向哪里',
    sub: '语系 → 濒危等级 → 是否有数字入口 · 流带宽度 = 语言数',
    family: '语系',
    level: '濒危等级',
    entry: '数字入口',
    hasWiki: '有维基版本',
    noWiki: '没有维基版本',
    others: '其他语系',
    othersSmall: (k: number, n: string) => `${k} 个小型语系 (${n})`,
    tail: (k: number, n: string) => `语系长尾很长：全库 ${k} 个语系，图里只单列了最大的 ${TOP_N} 个；`
      + `其余 ${n} 门语言合并在最后一条灰带里。`,
    merged: (n: number, k: number) => `「其他语系」合并了 ${k} 个语系、${n} 门语言`,
    hint: '点一条流带可以只高亮这条路径 · 双击空白处恢复',
    total: (n: string) => `${n} 门语言`,
    noAes: '没有濒危等级',
    leak: '看最右边的分叉：从任何语系出发，浅色（没有维基版本）的流带都远宽于深色。',
    why: '这不是某几个语系的问题 —— 每一列的前几条流带最后都汇入同一侧。',
  },
  en: {
    title: 'Where languages are flowing',
    sub: 'family → endangerment → digital entry · band width = number of languages',
    family: 'Family',
    level: 'Endangerment',
    entry: 'Digital entry',
    hasWiki: 'has Wikipedia',
    noWiki: 'no Wikipedia',
    others: 'other families',
    othersSmall: (k: number, n: string) => `${k} small families (${n})`,
    tail: (k: number, n: string) => `The family tail is long: ${k} families in total, `
      + `only the largest ${TOP_N} are shown individually; the remaining ${n} languages are pooled in the grey band at the bottom.`,
    merged: (n: number, k: number) => `"other families" pools ${k} families / ${n} languages`,
    hint: 'click a band to highlight that path · double-click empty space to reset',
    total: (n: string) => `${n} languages`,
    noAes: 'no status',
    leak: 'Look at the right-hand split: from every family, the pale band (no Wikipedia) is far wider than the dark one.',
    why: 'This is not a problem of a few families — every family’s widest band ends on the same side.',
  },
} as const

const t = computed(() => T[store.lang === 'zh' ? 'zh' : 'en'])

const LEVEL_LABEL = (lv: number): string => {
  const l = store.aes?.levels?.[String(lv)] ?? store.endangerment?.levels?.[String(lv)]
  if (!l) return String(lv)
  return store.lang === 'zh' ? (l.zh ?? l.en) : l.en
}

/** 濒危等级 1..6 的顺序色阶（与 EndangermentView 保持一致） */
const RAMP = [
  '#7c9a6a', '#c9b458', '#d9964a', '#cf6b3f', '#b34a35', '#7d3226',
]
const WIKI_COLOR = '#4a7c59'
const NOWIKI_COLOR = '#c9c3b6'

interface Node {
  name: string
  label: string
  depth: number
  color: string
  value: number
  labelPos?: 'left' | 'right'
}
interface Link { source: string; target: string; value: number }

const graph = computed(() => {
  const ebw = store.endangermentByWals
  const rows = store.langs
  const famAll = store.familyList
  const keep = new Set(famAll.slice(0, TOP_N).map((f) => f.family))
  const famColor = new Map<string, string>()
  famAll.slice(0, TOP_N).forEach((f, i) => famColor.set(f.family, PALETTE[i % PALETTE.length]))

  const familyOf = (l: (typeof rows)[number]) => {
    const f = l.family || '(未分类)'
    return keep.has(f) ? f : `__other`
  }

  // 统计三元组：语系 × 等级 × 有无维基
  const trip = new Map<string, number>()
  const famCount = new Map<string, number>()
  let othersLangs = 0
  const othersFams = new Set<string>()
  const levels = new Set<number>()
  let noAes = 0
  for (const l of rows) {
    const f = familyOf(l)
    if (f === '__other') {
      othersLangs += 1
      if (l.family) othersFams.add(l.family)
    }
    famCount.set(f, (famCount.get(f) ?? 0) + 1)
    const lv = ebw[l.wals_id]
    if (!lv) { noAes += 1; continue }
    levels.add(lv)
    const k = `${f}|${lv}|${l.wiki_code ? 1 : 0}`
    trip.set(k, (trip.get(k) ?? 0) + 1)
  }

  const nodes: Node[] = []
  const links: Link[] = []
  // 第一列：语系。
  // ⚠️ 必须**按语言数排序**并把「其他」放到最后 —— 之前按首次出现顺序，
  // 结果图里最宽的一条是「其他语系」(965 门)，比最大语系尼日尔-刚果(324)
  // 还宽，等于最显眼的位置放了个没有意义的灰块。
  // 语系长尾很长（共 254 个，前 14 个只覆盖 63.7%），所以这个桶本身无法避免，
  // 但至少要让真实语系占据上方，并把它的构成写进标签。
  const famOrder = [...famCount.entries()]
    .filter(([f]) => f !== '__other')
    .sort((a, b) => b[1] - a[1])
    .map(([f]) => f)
  if (famCount.has('__other')) famOrder.push('__other')
  for (const f of famOrder) {
    const isOther = f === '__other'
    nodes.push({
      name: `F:${f}`,
      label: isOther
        ? t.value.othersSmall(othersFams.size, othersLangs.toLocaleString('en-US'))
        : `${f} (${famCount.get(f)!.toLocaleString('en-US')})`,
      depth: 0,
      color: isOther ? C.neutral : (famColor.get(f) ?? C.neutral),
      value: famCount.get(f)!,
    })
  }
  // 第二列：濒危等级
  const lvList = [...levels].sort((a, b) => a - b)
  for (const lv of lvList) {
    nodes.push({
      name: `L:${lv}`,
      label: LEVEL_LABEL(lv),
      depth: 1,
      color: RAMP[lv - 1] ?? C.neutral,
      value: 0,
    })
  }
  // 第三列：数字入口
  nodes.push({ name: 'W:1', label: t.value.hasWiki, depth: 2, color: WIKI_COLOR, value: 0, labelPos: 'left' })
  nodes.push({ name: 'W:0', label: t.value.noWiki, depth: 2, color: NOWIKI_COLOR, value: 0, labelPos: 'left' })

  const lvTotals = new Map<string, number>()
  for (const [k, n] of trip) {
    const [f, lv, has] = k.split('|')
    links.push({ source: `F:${f}`, target: `L:${lv}`, value: n })
    links.push({ source: `L:${lv}`, target: `W:${has}`, value: n })
    lvTotals.set(`L:${lv}`, (lvTotals.get(`L:${lv}`) ?? 0) + n)
  }
  // 合并重复的 link（同一 source→target 可能被写多次）
  const merged = new Map<string, Link>()
  for (const l of links) {
    const key = `${l.source}>${l.target}`
    const cur = merged.get(key)
    if (cur) cur.value += l.value
    else merged.set(key, { ...l })
  }
  for (const n of nodes) {
    if (n.name.startsWith('L:')) n.value = lvTotals.get(n.name) ?? 0
    if (n.name === 'W:1') n.value = links.filter((l) => l.target === 'W:1').reduce((s, l) => s + l.value, 0)
    if (n.name === 'W:0') n.value = links.filter((l) => l.target === 'W:0').reduce((s, l) => s + l.value, 0)
  }
  return {
    nodes,
    links: [...merged.values()],
    othersFams: othersFams.size,
    othersLangs,
    famTotal: famAll.length,
    noAes,
  }
})

function buildOption() {
  const g = graph.value
  return {
    // 桑基图的节点顺序要稳定，否则每次重绘都会重排（视觉上像在跳）
    series: [{
      id: 'flow',
      type: 'sankey',
      left: 8, right: 128, top: 12, bottom: 12,
      nodeWidth: 12,
      nodeGap: 8,
      draggable: false,
      emphasis: { focus: 'adjacency' },
      // 关掉动画：桑基的重排动画在数据变化时会让人以为图在乱动
      animation: false,
      data: g.nodes.map((n) => ({
        name: n.name,
        itemStyle: { color: n.color, borderWidth: 0 },
        label: { position: n.labelPos ?? 'right' },
        // 显示名与内部名分开：内部名要唯一，显示名要好看
        __label: n.label,
      })),
      links: g.links.map((l) => ({
        source: l.source,
        target: l.target,
        value: l.value,
      })),
      lineStyle: {
        color: 'gradient',
        opacity: 0.32,
        curveness: 0.5,
      },
      label: {
        color: C.textSecondary,
        fontSize: 11,
        fontFamily: 'inherit',
      },
    }],
  }
}

const e = () => (window as any).echarts

function render() {
  if (!chart.value) return
  chart.value.setOption(buildOption(), true)
}

const { schedule: scheduleResize } = useChartResize(host, chart)

onMounted(() => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  render()
  scheduleResize()
})

onBeforeUnmount(() => {
  chart.value?.dispose()
})

watch(
  () => [store.endangermentLevels, store.lang, store.langs.length, store.aes, store.endangerment],
  () => render(),
)
watch(() => store.lang, () => render())
</script>

<template>
  <section class="card">
    <header>
      <div class="tl">
        <h2>{{ t.title }}</h2>
        <p class="sub">{{ t.sub }}</p>
      </div>
    </header>

    <div ref="host" class="chart" />

    <div class="foot">
      <p class="lead">{{ t.leak }}</p>
      <p class="note">{{ t.why }}</p>
      <p class="note">{{ t.tail(graph.famTotal, graph.othersLangs.toLocaleString('en-US')) }}</p>
    </div>
  </section>
</template>

<style scoped>
.card {
  display: flex; flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  min-height: 0; height: 100%;
  overflow: hidden;
}
header { flex: none; margin-bottom: var(--sp-2); }
.tl h2 { margin: 0; font-size: 1.02rem; font-weight: 600; }
.sub { margin: 3px 0 0; font-size: var(--fs-micro); color: var(--text-muted); }
.chart { flex: 1 1 auto; min-height: 0; width: 100%; }
.foot { flex: none; margin-top: var(--sp-2); }
.lead { margin: 0; font-size: var(--fs-small); color: var(--text-secondary); line-height: 1.7; }
.note { margin: 4px 0 0; font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.6; }
</style>
