/**
 * 故事模式：引导式线性叙事。
 *
 * 对应设计文档 §6 的「故事模式：引导式线性叙事」与老师注意点 2（导航设计）。
 *
 * **一个刻意的决定：文案里的数字全部实时算，不写死。**
 * 这个项目已经因为把数字写死在文档里吃过好几次亏（时间序列 55,427→66,103、
 * 可关联 247→271、月份 127→135…），故事模式的文案是最容易被反复读的地方，
 * 更不能让它在数据更新后变成假话。所以每步的正文是 `(store) => string`。
 *
 * 每步只做两件事：把看板切到那个视图、设好那组筛选；文字负责把"该看什么"讲出来。
 * 状态仍然走同一个 store，所以**故事里任何一步都可以用 URL 分享**。
 */
import type { useDataset } from '@/stores/dataset'
import { hasCoords } from '@/types'

type Store = ReturnType<typeof useDataset>

export interface StoryStep {
  key: string
  /** 进入这一步时把看板切到这个视图 */
  view: Store['activeView']
  zh: { title: string; body: (s: Store, f: Facts) => string; note?: string }
  en: { title: string; body: (s: Store, f: Facts) => string; note?: string }
  /** 设置这一步需要的筛选与选中状态 */
  enter: (s: Store) => void
}

/* ------------------------------------------------------------------ 实时统计 */

export interface Facts {
  total: number
  coords: number
  wiki: number
  wikiRate: number
  reliable: number
  worst: { name: string; g: number }[]
  best: { name: string; g: number }[]
  /** 濒危等级 → { 语言数, 有维基数, 比例 } */
  byLevel: Record<number, { n: number; wiki: number; rate: number }>
  /** 记录完整度分桶 → { 语言数, 有维基比例 } */
  absence: { label: string; n: number; rate: number }[]
  featureCells: { features: number; langs: number; filled: number }
  /** 已灭绝/几近灭绝但有维基版本的（数字续命的那几门） */
  revived: { name: string; growth: number | null; views: number | null; level: number }[]
}

const pct = (x: number) => `${(x * 100).toFixed(1)}%`

/** 把 story 需要的一切从当前数据里算出来（随数据变化，不会过期） */
export function storyFacts(s: Store): Facts {
  const all = s.langs
  const withCn = (l: (typeof all)[number]) => {
    const d = s.zhLabels
    const cn = d
      ? (d.by_iso639p3[(l.iso639p3 || '').toLowerCase()] || d.by_glottocode[l.glottocode || ''])
      : null
    return cn || l.name
  }
  const wikiRows = all.filter((l) => l.wiki_code)
  const reliable = all.filter((l) => l.baseline_ok && l.growth != null)
    .slice().sort((a, b) => a.growth! - b.growth!)

  const ebw = s.endangermentByWals
  const byLevel: Facts['byLevel'] = {}
  for (let lv = 1; lv <= 6; lv++) {
    const rows = all.filter((l) => ebw[l.wals_id] === lv)
    const w = rows.filter((l) => l.wiki_code).length
    byLevel[lv] = { n: rows.length, wiki: w, rate: rows.length ? w / rows.length : 0 }
  }

  const fc = s.featureCount
  const buckets = [
    { label: '< 30', lo: 0, hi: 30 },
    { label: '30–79', lo: 30, hi: 80 },
    { label: '80–149', lo: 80, hi: 150 },
    { label: '≥ 150', lo: 150, hi: Infinity },
  ]
  const absence = buckets.map((b) => {
    const rows = all.filter((l) => {
      const c = fc[l.wals_id] ?? 0
      return c >= b.lo && c < b.hi
    })
    const w = rows.filter((l) => l.wiki_code).length
    return { label: b.label, n: rows.length, rate: rows.length ? w / rows.length : 0 }
  })

  const m = s.matrix
  const filled = m
    ? m.values.reduce((acc, row) => acc + row.filter((v) => v != null).length, 0)
    : 0

  const revived = all
    .filter((l) => (ebw[l.wals_id] ?? 0) >= 5 && l.wiki_code)
    .sort((a, b) => (b.views_recent ?? 0) - (a.views_recent ?? 0))
    .map((l) => ({
      name: withCn(l), growth: l.growth ?? null,
      views: l.views_recent ?? null, level: ebw[l.wals_id],
    }))

  const mk = (l: (typeof all)[number]) => ({ name: withCn(l), g: l.growth! })
  return {
    total: all.length,
    coords: all.filter(hasCoords).length,
    wiki: wikiRows.length,
    wikiRate: all.length ? wikiRows.length / all.length : 0,
    reliable: reliable.length,
    worst: reliable.slice(0, 3).map(mk),
    best: reliable.slice(-3).reverse().map(mk),
    byLevel, absence, revived,
    featureCells: {
      features: m?.feature_ids.length ?? 0,
      langs: m?.language_keys.length ?? 0,
      filled,
    },
  }
}

/* -------------------------------------------------------------------- 步 骤 */

/** 每步进入时的通用清理：先清空筛选，避免上一步的条件残留 */
function reset(s: Store) {
  s.clearFilters()
  s.selected = null
  s.hideUnselected = false
  s.showVitality = true
  s.colorBy = 'macroarea'
  s.sizeMode = 'relative'
}

const joined = (xs: { name: string; g: number }[], fmt: (g: number) => string) =>
  xs.map((x) => `${x.name} ${fmt(x.g)}`).join('、')

export const STORY: StoryStep[] = [
  {
    key: 'where',
    view: 'map',
    zh: {
      title: '这些语言在哪里',
      body: (_s, f) =>
        `地图上是 ${f.total.toLocaleString('en-US')} 门语言，其中 ${f.coords.toLocaleString('en-US')} 门有坐标。`
        + `每一个点是一门语言，颜色代表它所属的语区。`
        + `\n\n先把"语言在哪里"看清楚，因为后面每一个问题都要落回这张地图。`,
    },
    en: {
      title: 'Where are these languages?',
      body: (_s, f) =>
        `${f.total.toLocaleString('en-US')} languages, ${f.coords.toLocaleString('en-US')} of them with coordinates.`
        + ` Each dot is one language; colour is its macro-area.`
        + `\n\nStart here — every later question lands back on this map.`,
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'map'
      s.monthIndex = Math.max(s.months.length - 1, 0)
    },
  },
  {
    key: 'gate',
    view: 'map',
    zh: {
      title: '但绝大多数在数字世界没有入口',
      body: (_s, f) =>
        `${f.total.toLocaleString('en-US')} 门语言里，只有 ${f.wiki.toLocaleString('en-US')} 门`
        + `（${pct(f.wikiRate)}）拥有维基百科版本。`
        + `\n\n其余 ${(f.total - f.wiki).toLocaleString('en-US')} 门在互联网上没有自己的入口 ——`
        + `不是"内容少"，是**根本不存在**。点开「活力层」，地图上放大的那些才是有版本的。`,
      note: '想要一个维基百科版本，需要社群推动与官方审批 —— 这是一道很高的组织门槛。',
    },
    en: {
      title: 'Most have no digital entry point',
      body: (_s, f) =>
        `Of ${f.total.toLocaleString('en-US')} languages only ${f.wiki.toLocaleString('en-US')}`
        + ` (${pct(f.wikiRate)}) have a Wikipedia edition.`
        + `\n\nThe other ${(f.total - f.wiki).toLocaleString('en-US')} have no entry point online —`
        + ` not "little content", but **nothing at all**.`,
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'map'
      s.showVitality = true
      s.monthIndex = Math.max(s.months.length - 1, 0)
    },
  },
  {
    key: 'trend',
    view: 'growth',
    zh: {
      title: '有入口的那些，十年里在退还是在进',
      body: (_s, f) =>
        `用首末各 3 个月的均值算十年变化，${f.reliable} 门语言的基线足够可靠、能算。`
        + `\n\n**在退的**：${joined(f.worst, (g) => pct(g))}`
        + `\n**在进的**：${joined(f.best, (g) => (g >= 0 ? '+' : '') + (g * 100).toFixed(0) + '%')}`
        + `\n\n注意增长榜前列里有濒危语言 —— 它们的基数极小。这一点后面会再回来。`,
    },
    en: {
      title: 'Among those present, who grew and who declined?',
      body: (_s, f) =>
        `Using the first and last 3-month means, ${f.reliable} languages have a reliable baseline.`
        + `\n\n**Declining**: ${joined(f.worst, (g) => pct(g))}`
        + `\n**Growing**: ${joined(f.best, (g) => (g >= 0 ? '+' : '') + (g * 100).toFixed(0) + '%')}`,
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'growth'
    },
  },
  {
    key: 'docs',
    view: 'matrix',
    zh: {
      title: '但先看一个更基础的问题：记录本身就不平等',
      body: (_s, f) =>
        `语言学数据库 WALS 收录了 ${f.featureCells.langs.toLocaleString('en-US')} 门语言`
        + ` × ${f.featureCells.features} 个语法特征，但${f.featureCells.langs * f.featureCells.features > 0
          ? `只有 ${(f.featureCells.filled / (f.featureCells.langs * f.featureCells.features) * 100).toFixed(1)}% 有值`
          : '大量格子是空的'}。`
        + `\n\n这张图横轴是特征、纵轴是语言，颜色是"这一行里有记录的比例"。`
        + `左上角红、右下角白 —— 记录高度集中在少数语言和少数特征上。`,
      note: '所以"某门语言没有这个特征"和"没人研究过这门语言的这个特征"，在数据里长得一样。',
    },
    en: {
      title: 'First, a more basic problem: documentation itself is unequal',
      body: (_s, f) =>
        `WALS covers ${f.featureCells.langs.toLocaleString('en-US')} languages × ${f.featureCells.features} features,`
        + ` but only ${(f.featureCells.filled / (f.featureCells.langs * f.featureCells.features) * 100).toFixed(1)}% of cells are filled.`
        + `\n\nHorizontal axis: features. Vertical: languages. Colour: the share of that row band with a record.`,
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'matrix'
    },
  },
  {
    key: 'double',
    view: 'matrix',
    zh: {
      title: '于是有了「双重缺席」',
      body: (_s, f) => {
        const a = f.absence[0]
        const b = f.absence[f.absence.length - 1]
        return `把语言按"被记录了多少个特征"分桶，再看它们有没有维基百科版本：`
          + `\n\n**记录 < 30 个特征**的 ${a.n.toLocaleString('en-US')} 门里，只有 ${pct(a.rate)} 有版本；`
          + `\n**记录 ≥ 150 个特征**的 ${b.n.toLocaleString('en-US')} 门里，${pct(b.rate)} 有版本。`
          + `\n\n语言学界记录得越少的语言，在数字世界里往往也越不可见。`
          + `两件本来分属不同领域的偏差，叠在了一起 —— 这就是下面那块柱状图。`
      },
    },
    en: {
      title: 'Hence “double absence”',
      body: (_s, f) => {
        const a = f.absence[0]
        const b = f.absence[f.absence.length - 1]
        return `Bin languages by how many features are recorded, then look at whether they have a Wikipedia:`
          + `\n\nfewer than 30 features: ${pct(a.rate)} of ${a.n.toLocaleString('en-US')}`
          + `\n150 or more: ${pct(b.rate)} of ${b.n.toLocaleString('en-US')}`
      },
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'matrix'
    },
  },
  {
    key: 'twoVitalities',
    view: 'endanger',
    zh: {
      title: '现在把两个「活力」摆在一起',
      body: (_s, f) => {
        const l1 = f.byLevel[1]
        const l6 = f.byLevel[6]
        return `前面所有叫"活力"的指标，其实都来自维基浏览量 —— 那是**数字关注度**，`
          + `不是语言学意义上的语言活力。`
          + `\n\n接上 Glottolog / UNESCO 的濒危等级后可以对照了：`
          + `\n**未濒危**的 ${l1.n.toLocaleString('en-US')} 门里 ${pct(l1.rate)} 有维基版本；`
          + `\n**已灭绝**的 ${l6.n.toLocaleString('en-US')} 门里只有 ${l6.wiki} 门有。`
          + `\n\n一门语言在语言学上还活着，但在数字空间里已经死了吗？—— 数据说：这两件事高度重合。`
      },
    },
    en: {
      title: 'Now put the two kinds of “vitality” side by side',
      body: (_s, f) => {
        const l1 = f.byLevel[1]
        const l6 = f.byLevel[6]
        return `Everything called “vitality” so far came from pageviews — that is **digital attention**,`
          + ` not linguistic vitality.`
          + `\n\nWith endangerment levels joined in: ${pct(l1.rate)} of the ${l1.n.toLocaleString('en-US')} not-endangered languages`
          + ` have a Wikipedia, versus ${l6.wiki} of the ${l6.n.toLocaleString('en-US')} extinct ones.`
      },
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'endanger'
    },
  },
  {
    key: 'revival',
    view: 'endanger',
    zh: {
      title: '但数字空间也在「续命」',
      body: (_s, f) => {
        if (!f.revived.length) return '当前数据里没有已灭绝却仍有维基版本的语言。'
        const top = f.revived.slice(0, 3)
        const lines = top.map((r) =>
          `${r.name}（${r.level >= 6 ? '已灭绝' : '几近灭绝'}）`
          + `${r.growth != null ? `，十年 ${r.growth >= 0 ? '+' : ''}${(r.growth * 100).toFixed(0)}%` : ''}`
          + `${r.views ? `，月阅读 ${Math.round(r.views).toLocaleString('en-US')}` : ''}`)
        return `别急着下结论。把筛选设成「已灭绝 / 几近灭绝」，会发现仍有 ${f.revived.length} 门语言拥有维基版本：`
          + `\n\n${lines.join('\n')}`
          + `\n\n康沃尔语最后一位母语者 1777 年去世，马恩岛语最后一位 1974 年 ——`
          + `作为口语它们已经消失，但在数字空间里**反而在增长**。这是语言复兴运动的痕迹。`
      },
      note: '所以「数字缺席」不是单向的：它既能抛弃一门语言，也能替一门语言续命。',
    },
    en: {
      title: 'But the digital space also keeps languages alive',
      body: (_s, f) => {
        if (!f.revived.length) return 'No extinct-but-present languages in the current data.'
        return `Set the filter to extinct / nearly extinct and ${f.revived.length} languages still have a Wikipedia:`
          + `\n\n${f.revived.slice(0, 3).map((r) => `${r.name}`).join('、')}`
          + `\n\nCornish lost its last native speaker in 1777, Manx in 1974 —`
          + ` dead as vernaculars, yet **growing online**.`
      },
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'endanger'
      // 只留「几近灭绝 / 已灭绝」两档，让上面那几门浮出来
      s.endangermentLevels = [5, 6]
    },
  },
  {
    key: 'yours',
    view: 'map',
    zh: {
      title: '现在换你来问',
      body: (_s, f) =>
        `故事到这里。回到地图，${f.total.toLocaleString('en-US')} 门语言都在上面。`
        + `\n\n你可以用左侧自由筛选，也可以直接在底部**用一句话提问**，`
        + `比如「极度濒危的语言」「非洲语区里语序是 SOV 且在增长的语言」。`
        + `\n\n右上角「复制链接」能把当前画面变成一条可以分享的网址。`,
    },
    en: {
      title: 'Your turn',
      body: (_s, f) =>
        `That is the story. Back on the map, all ${f.total.toLocaleString('en-US')} languages are there.`
        + `\n\nFilter freely on the left, or just **ask in one sentence** at the bottom.`
        + `\n\n“Copy link” in the header turns the current view into a shareable URL.`,
    },
    enter: (s) => {
      reset(s)
      s.activeView = 'map'
    },
  },
]
