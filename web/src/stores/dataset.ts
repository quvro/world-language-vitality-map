/**
 * 全局数据集与交互状态。
 *
 * 所有视图只读这个 store、彼此不直接调用 —— 这是"任一处选中、全局同步"
 * (Brushing & Linking) 能成立的前提，也让新增视图不需要改别的模块。
 *
 * 按设计文档 §10.3，选中状态同时维护 `selected`（单个）与 `comparisonSet`
 * （多个），这样将来加"多语言并排对比"不必重构选中逻辑。
 */
import { defineStore } from 'pinia'
import { SEARCH_ALIASES } from '@/terms'
import { STORY } from '@/story'
import { MACRO_AREAS } from '@/types'
import type {
  FeatureMatrix, Features, Language, MacroArea, Timeseries,
} from '@/types'

const DATA = '/data/processed/'

export interface ZhLabels {
  by_iso639p3: Record<string, string>
  by_glottocode: Record<string, string>
  macroarea: Record<string, string>
  family: Record<string, string>
}

/**
 * 统一的「濒危等级」量表（1 未濒危 … 6 已灭绝）。
 *
 * 两个数据源的 6 级是**一一对应**的（依据 Glottolog CLDF codes.csv 的说明）：
 *   1 not endangered = UNESCO safe            2 threatened   = UNESCO vulnerable
 *   3 shifting       = UNESCO definitely      4 moribund     = UNESCO severely
 *   5 nearly extinct = UNESCO critically      6 extinct      = UNESCO extinct
 * 所以可以合并成一个量表：**AES 优先，UNESCO 补缺**。
 *
 * 为什么以 AES 为主：UNESCO 名录**只收濒危语言**（全名录 2,593 条里只有 82 条 safe），
 * 本项目只能匹配上 41.9%，没有"未濒危"这一档作参照，散点图会严重偏斜。
 * AES 给所有 languoid 都标了级，覆盖 97.3%。
 *
 * 合并后覆盖 2,614 / 2,662 = 98.2%。
 */
export interface Aes {
  levels: Record<string, { en: string; zh: string; desc?: string }>
  by_glottocode: Record<string, number>
  counts: Record<string, number>
}

export interface Endangerment {
  levels: Record<string, { en: string; zh: string }>
  by_glottocode: Record<string, number>
  by_iso639p3: Record<string, number>
  counts: Record<string, number>
}

/** 07_fetch_digital_presence.py 的产出：维基项目数 + Glottolog 描述深度 */
export interface DigitalPresence {
  by_wiki_code: Record<string, {
    projects: string[]
    n: number
    n_extra: number
  }>
  by_glottocode: Record<string, {
    /** Glottolog med 原始编码值（0 最好、4 最差 —— 刻度是反的） */
    raw: number
    /** 已转成"越高越好"：5 = 长篇参考语法，1 = 词表或更少 */
    depth: number
    code: string
    label_zh: string
    label_en: string
  }>
  meta: {
    sitematrix_languages: number
    with_extra_projects: number
    med_languages: number
    med_scale: { note: string; labels: Record<string, string> }
  }
}

async function loadJson<T>(file: string): Promise<T> {
  const res = await fetch(DATA + file)
  if (!res.ok) throw new Error(`${file} 加载失败：HTTP ${res.status}`)
  return res.json() as Promise<T>
}

interface State {
  langs: Language[]
  timeseries: Timeseries | null
  features: Features | null
  matrix: FeatureMatrix | null
  /** Wikidata 抓来的中文标签；缺失时界面自动回退英文 */
  zhLabels: ZhLabels | null
  endangerment: Endangerment | null
  aes: Aes | null
  presence: DigitalPresence | null
  loading: boolean
  error: string | null
  /** wals_id -> 在 feature_matrix.language_keys 里的下标，加载后预计算避免每次线性查找 */
  keyIndex: Record<string, number>

  /** 语区筛选；空集表示不过滤 */
  macroAreas: MacroArea[]
  /** 语系筛选；空集表示不过滤 */
  families: string[]
  /** 只显示基线可靠（增长率可信）的语言 */
  onlyReliable: boolean
  search: string
  /**
   * 按某个语法特征的某个取值筛选（来自「条件对比」里点选的分组，
   * 或自然语言查询）。`value` 为 null 表示「只要有该特征的数据」。
   */
  featureFilter: { featureId: string; value: string | null } | null
  /** 当前用于分组对比的特征 */
  compareFeature: string | null

  // ---- 以下由自然语言查询写入，也在筛选面板里显示为可清除的条件 ----
  growthMin: number | null
  growthMax: number | null
  wikiOnly: boolean
  minFeatures: number | null
  /** UNESCO 濒危等级（1..6）多选；空数组表示不按濒危程度筛选 */
  endangermentLevels: number[]

  /**
   * 主视图。新增视图时**必须同步加进这个联合类型** ——
   * 之前加了「记录缺口」和「濒危 × 关注」两个选项卡却忘了改这里，
   * 于是 `vue-tsc` 报 TS2322/TS2367，`pnpm build` 直接失败。
   * 开发时 Vite 只转译不做类型检查，所以这个错误藏了很久。
   */
  activeView: 'map' | 'growth' | 'features' | 'matrix' | 'endanger'
  /**
   * 故事模式的当前步（null = 探索模式）。
   *
   * 放在 store 而不是组件局部状态，是为了两件事：
   *   1. 每一步都能进 URL，**故事里任何一屏都可以分享**
   *   2. `goStory()` 直接复用同一套筛选字段，故事与自由探索不各搞一套状态
   */
  storyStep: number | null
  /**
   * 地图着色依据。
   *
   * 注意这里**没有**「有时间 / 没时间」的模式开关：活力层永远在线、永远由
   * 时间轴驱动大小。早期版本用「分布 / 活力」两个模式互斥切换，导致在分布
   * 模式下拖时间轴毫无反应 —— 那是设计缺陷，不是 bug，所以直接去掉。
   */
  colorBy: 'macroarea' | 'trend'
  /** 是否叠加活力层（关掉可看纯粹的语区分布） */
  showVitality: boolean
  /**
   * 地图底图的渲染方式：密度块 / 逐点。
   *
   * **刻意做成用户显式切换，而不是跟随缩放自动切换。**
   * 自动切换需要在漫游过程中 setOption，那会打断 geo 的缩放补间，
   * 让渲染出的地图与模型里的 zoom/center 不一致（表现为"缩放时地图错位，
   * 点一下又复位"）。去掉这条路径后，缩放期间不再发生任何 setOption。
   */
  mapDensity: boolean
  /** 只看选中的语言 —— 选中后其余点全部隐藏，便于在一堆点里找到它 */
  hideUnselected: boolean
  /**
   * 点的大小依据。
   *
   * relative —— 相对该语言**自身十年峰值**。默认用这个：实测拖时间轴时
   *   尺寸中位变化 1.96px、59% 的变化肉眼可辨。
   * absolute —— 跨语言绝对比较。但德语维基月浏览约 7 亿、多数语言只有几千，
   *   开方压缩后中位变化仅 0.05px（0.3% 可辨），**等于没有动画**。所以改用当月排名分位。
   */
  sizeMode: 'relative' | 'absolute'
  /** 界面语言 */
  lang: 'zh' | 'en'

  /** 底部时间轴位置 */
  monthIndex: number
  playing: boolean

  selected: string | null
  comparisonSet: string[]
}

export const useDataset = defineStore('dataset', {
  state: (): State => ({
    langs: [],
    timeseries: null,
    features: null,
    matrix: null,
    zhLabels: null,
    endangerment: null,
    aes: null,
    presence: null,
    loading: true,
    error: null,
    keyIndex: {},
    macroAreas: [],
    families: [],
    onlyReliable: false,
    search: '',
    featureFilter: null,
    compareFeature: null,
    growthMin: null,
    growthMax: null,
    wikiOnly: false,
    minFeatures: null,
    endangermentLevels: [],
    activeView: 'map',
    storyStep: null,
    colorBy: 'macroarea',
    showVitality: true,
    mapDensity: true,
    hideUnselected: false,
    sizeMode: 'relative',
    lang: 'zh',
    monthIndex: 0,
    playing: false,
    selected: null,
    comparisonSet: [],
  }),

  getters: {
    /** 全部月份，升序（YYYYMM） */
    months(state): string[] {
      const sample = Object.values(state.timeseries?.by_language ?? {})[0]
      if (!sample) return []
      return Object.keys(sample.views).sort()
    },

    currentMonth(): string {
      return this.months[this.monthIndex] ?? ''
    },

    /** 有维基时间序列、且能算增长率的语言 */
    withVitality(state): Language[] {
      return state.langs.filter((l) => l.wiki_code && l.views_baseline != null)
    },

    /** 语系列表（按语言数降序），用于筛选面板 */
    familyList(state): { family: string; count: number }[] {
      const map = new Map<string, number>()
      for (const l of state.langs) {
        const f = l.family || '(未分类)'
        map.set(f, (map.get(f) ?? 0) + 1)
      }
      return [...map.entries()]
        .map(([family, count]) => ({ family, count }))
        .sort((a, b) => b.count - a.count)
    },

    /**
     * 基础筛选结果（**不含**按特征取值的筛选）。
     *
     * 「条件对比」必须在这个集合上分组：如果用它算完之后的结果再分组，
     * 点选一个分组就会让其它分组消失、对比图自己塌掉。
     */
    filteredBase(state): Language[] {
      const q = state.search.trim().toLowerCase()
      const dict = state.zhLabels
      const fc = this.featureCount
      const ebw = this.endangermentByWals
      const lvSel = state.endangermentLevels
      return state.langs.filter((l) => {
        if (state.macroAreas.length && !state.macroAreas.includes(l.macroarea as MacroArea)) {
          return false
        }
        if (state.families.length && !state.families.includes(l.family || '(未分类)')) {
          return false
        }
        if (state.onlyReliable && !(l.baseline_ok && l.growth != null)) return false
        // ---- 自然语言查询写入的条件 ----
        if (state.wikiOnly && !l.wiki_code) return false
        // 按 UNESCO 濒危等级筛选。注意：只选等级时，未被名录收录的语言会被排除 ——
        // 这是符合直觉的（"极度濒危"当然只应包含名录里标为极度濒危的）。
        if (lvSel.length && !lvSel.includes(ebw[l.wals_id] ?? 0)) return false
        if (state.minFeatures != null && (fc[l.wals_id] ?? 0) < state.minFeatures) return false
        if (state.growthMin != null || state.growthMax != null) {
          // 没有增长率数据的语言在按增长筛选时直接排除（「在增长」不可能对未知成立）
          const g = l.growth != null && l.baseline_ok ? l.growth * 100 : null
          if (g == null) return false
          if (state.growthMin != null && g < state.growthMin) return false
          if (state.growthMax != null && g > state.growthMax) return false
        }
        if (q) {
          // 除中英名外还要匹配别名 —— 否则搜「中文」「普通话」找不到 Mandarin
          // （WALS 把它叫 Mandarin，而 Wikidata 的中文标签是「官话」）
          const iso = (l.iso639p3 || '').toLowerCase()
          const parts = [l.name]
          if (dict) {
            const cn = (iso && dict.by_iso639p3[iso]) ||
              (l.glottocode && dict.by_glottocode[l.glottocode])
            if (cn) parts.push(cn)
          }
          if (iso) {
            parts.push(iso)
            const alias = SEARCH_ALIASES[iso]
            if (alias) parts.push(...alias)
          }
          if (l.wiki_code) parts.push(l.wiki_code)
          if (!parts.join(' ').toLowerCase().includes(q)) return false
        }
        return true
      })
    },

    /** 全站生效的筛选结果 = 基础筛选 +（可选）特征取值筛选 */
    filtered(): Language[] {
      const base = this.filteredBase
      const ff = this.featureFilter
      if (!ff || !this.matrix) return base
      const fi = this.matrix.feature_ids.indexOf(ff.featureId)
      if (fi < 0) return base
      const row = this.matrix.values[fi]
      return base.filter((l) => {
        const i = this.keyIndex[l.wals_id]
        if (i == null) return false
        // value 为 null 表示「只要有该特征的数据」，不限定具体取值
        return ff.value == null ? row[i] != null : row[i] === ff.value
      })
    },

    /** 某门语言在某个特征上的取值（原始 Value，用于定位 codes 里的 Number） */
    featureValueOf(state) {
      return (walsId: string, featureId: string): string | null => {
        if (!state.matrix) return null
        const fi = state.matrix.feature_ids.indexOf(featureId)
        const i = state.keyIndex[walsId]
        if (fi < 0 || i == null) return null
        return state.matrix.values[fi][i] ?? null
      }
    },

    /** (featureId, Number) -> 取值的中文/英文名称 */
    codeLabel(state) {
      const m = new Map<string, string>()
      for (const c of state.features?.codes ?? []) {
        m.set(`${c.Parameter_ID}\u0000${c.Number}`, c.Name || c.Description || c.ID)
      }
      return m
    },

    selectedLanguage(state): Language | null {
      return state.langs.find((l) => l.wals_id === state.selected) ?? null
    },

    /** 当月每个语言的浏览量（按 wals_id 索引） */
    currentViews(state): Record<string, number> {
      const month = this.currentMonth
      const out: Record<string, number> = {}
      if (!month || !state.timeseries) return out
      for (const [wid, series] of Object.entries(state.timeseries.by_language)) {
        const v = series.views[month]
        if (v != null) out[wid] = v
      }
      return out
    },

    /** 当月最大浏览量，用于把点的大小映射到像素 */
    currentMax(): number {
      const vals = Object.values(this.currentViews)
      return vals.length ? Math.max(...vals) : 1
    },

    /**
     * 每门语言十年内的月度浏览量峰值。
     * 「相对自身」尺度需要它：否则单一巨型语种（德语维基月浏览约 7 亿）会把
     * 其它语言全压到最小尺寸，拖时间轴时中位变化只有 0.05px，等于没有动画。
     */
    ownPeak(state): Record<string, number> {
      const out: Record<string, number> = {}
      for (const [wid, s] of Object.entries(state.timeseries?.by_language ?? {})) {
        let mx = 0
        for (const v of Object.values(s.views)) if (v > mx) mx = v
        out[wid] = mx || 1
      }
      return out
    },

    /** 当月按浏览量的排名（0 = 第一），「绝对比较」尺度用 */
    currentRank(): Record<string, number> {
      const entries = Object.entries(this.currentViews).sort((a, b) => b[1] - a[1])
      const out: Record<string, number> = {}
      entries.forEach(([wid], i) => { out[wid] = i })
      return out
    },

    /** 当前筛选命中的语言集合 —— 地图用它决定哪些点淡出（而不是消失） */
    matchedIds(): Set<string> {
      return new Set(this.filtered.map((l) => l.wals_id))
    },

    /**
     * wals_id → 统一濒危等级（1..6）。未被覆盖的语言没有键。
     *
     * **AES 优先，UNESCO 补缺** —— 两者 6 级一一对应，理由见 Aes 的注释。
     * 粒度注意：濒危状态是**语言级**的，而本项目分析单元是**变体级**，
     * 所以同一 Glottocode 下的多个变体会得到同一等级（这是正确的）。
     */
    endangermentByWals(state): Record<string, number> {
      const e = state.endangerment
      const a = state.aes
      if (!e && !a) return {}
      const out: Record<string, number> = {}
      for (const l of state.langs) {
        const gc = l.glottocode ?? ''
        const iso = (l.iso639p3 ?? '').toLowerCase()
        const lv = a?.by_glottocode[gc] ??
          // UNESCO 只有 Glottocode 没命中时才用 ISO 兜底
          e?.by_glottocode[gc] ?? e?.by_iso639p3[iso]
        if (lv) out[l.wals_id] = lv
      }
      return out
    },

    /**
     * 描述深度（Glottolog `med`）：这门语言有多少"最详尽的描写文献"。
     *
     * ⚠️ Glottolog 的原始编码是**反向**的（0 = 长篇参考语法，4 = 词表或更少），
     * 管道 07 已经转成 `depth`（5 = 最好，1 = 最差），这里直接用 depth，
     * 免得前端再翻一次轴。
     */
    descDepth(state): Record<string, {
      depth: number; raw: number; label_zh: string; label_en: string
    }> {
      const p = state.presence
      if (!p) return {}
      const out: Record<string, { depth: number; raw: number; label_zh: string; label_en: string }> = {}
      for (const l of state.langs) {
        const d = p.by_glottocode[l.glottocode ?? '']
        if (d) out[l.wals_id] = d
      }
      return out
    },

    /**
     * 维基媒体项目数：**除维基百科之外**还有几个项目（词典/文库/新闻/教科书…）。
     * 有多个项目的语言通常意味着存在持续的编辑社群，而不只是被写进百科全书。
     * 实测：有维基版本的 267 门里，138 门有 ≥2 个额外项目。
     */
    wikiProjects(state): Record<string, {
      n: number; n_extra: number; projects: string[]
    }> {
      const p = state.presence
      if (!p) return {}
      const out: Record<string, { n: number; n_extra: number; projects: string[] }> = {}
      for (const l of state.langs) {
        const d = p.by_wiki_code[l.wiki_code ?? '']
        if (d) out[l.wals_id] = d
      }
      return out
    },

    /** 用的是哪个数据源（给口径说明用） */
    endangermentSources(state): { aes: number; unescoOnly: number; none: number } {
      const a = state.aes?.by_glottocode ?? {}
      const e = state.endangerment
      let aes = 0
      let unescoOnly = 0
      let none = 0
      for (const l of state.langs) {
        const gc = l.glottocode ?? ''
        const iso = (l.iso639p3 ?? '').toLowerCase()
        if (a[gc]) aes++
        else if (e?.by_glottocode[gc] ?? e?.by_iso639p3[iso]) unescoOnly++
        else none++
      }
      return { aes, unescoOnly, none }
    },

    /**
     * 每门语言在 WALS 里被收录了多少个语法特征（数据完整度）。
     * 自然语言里的「数据完整的语言」需要它。2660×192 ≈ 51 万次取值，
     * 实测约 6ms，且 getter 有缓存，不必额外落库。
     */
    featureCount(state): Record<string, number> {
      const out: Record<string, number> = {}
      const m = state.matrix
      if (!m) return out
      m.language_keys.forEach((k, i) => {
        let n = 0
        for (let fi = 0; fi < m.values.length; fi++) {
          if (m.values[fi][i] != null) n++
        }
        out[k] = n
      })
      return out
    },

    /** 是否有任何筛选生效（含特征分组与自然语言写入的条件） */
    hasFilter(state): boolean {
      return state.macroAreas.length > 0 || state.families.length > 0 ||
        state.onlyReliable || !!state.search.trim() || !!state.featureFilter ||
        state.wikiOnly || state.minFeatures != null ||
        state.growthMin != null || state.growthMax != null ||
        state.endangermentLevels.length > 0
    },
  },

  actions: {
    async load() {
      this.loading = true
      this.error = null
      try {
        const [langs, timeseries, features, matrix] = await Promise.all([
          loadJson<Language[]>('languages.json'),
          loadJson<Timeseries>('timeseries.json'),
          loadJson<Features>('features.json'),
          loadJson<FeatureMatrix>('feature_matrix.json'),
        ])
        this.langs = langs
        this.timeseries = timeseries
        this.features = features
        this.matrix = matrix
        // 中文标签是可选的：还没跑 04 脚本时不应该让整个应用报错
        try {
          this.zhLabels = await loadJson<ZhLabels>('zh_labels.json')
        } catch {
          this.zhLabels = null
        }
        // UNESCO 濒危等级也是可选的（跑过 05 脚本才有）
        try {
          this.endangerment = await loadJson<Endangerment>('endangerment.json')
        } catch {
          this.endangerment = null
        }
        // Glottolog AES（跑过 06 脚本才有）。它覆盖面大得多，优先使用。
        try {
          this.aes = await loadJson<Aes>('aes.json')
        } catch {
          this.aes = null
        }
        // 维基媒体项目数 + Glottolog 描述深度（跑过 07 脚本才有）
        try {
          this.presence = await loadJson<DigitalPresence>('digital_presence.json')
        } catch {
          this.presence = null
        }

        // 预计算下标，避免筛选时对 2,660 条做线性查找
        const idx: Record<string, number> = {}
        matrix.language_keys.forEach((k, i) => { idx[k] = i })
        this.keyIndex = idx

        // 默认对比特征：**自动挑分组差异最大的那个**。
        // 语序这类"常识型"特征其实差异极小（实测 SVO 15% vs SOV 10%，仅 4 个百分点），
        // 默认展示它会让整个界面显得没信息；而差异最大的特征可达 80+ 个百分点。
        const spreadOf = (fid: string): number => {
          const fi = matrix.feature_ids.indexOf(fid)
          if (fi < 0) return 0
          const row = matrix.values[fi]
          const acc = new Map<string, { t: number; w: number }>()
          for (const l of langs) {
            const i = idx[l.wals_id]
            if (i == null) continue
            const v = row[i]
            if (v == null) continue
            let a = acc.get(v)
            if (!a) { a = { t: 0, w: 0 }; acc.set(v, a) }
            a.t++
            if (l.wiki_code) a.w++
          }
          const rates: number[] = []
          for (const a of acc.values()) if (a.t >= 12) rates.push(a.w / a.t)
          return rates.length < 2 ? 0 : Math.max(...rates) - Math.min(...rates)
        }
        let best: string | null = null
        let bestSpread = -1
        for (const fid of matrix.feature_ids) {
          const s = spreadOf(fid)
          if (s > bestSpread) { bestSpread = s; best = fid }
        }
        this.compareFeature = best ?? features.features[0]?.ID ?? null

        // 时间轴默认停在最新月份
        this.monthIndex = Math.max(0, this.months.length - 1)
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    },

    toggleMacroArea(m: MacroArea) {
      const i = this.macroAreas.indexOf(m)
      if (i >= 0) this.macroAreas.splice(i, 1)
      else this.macroAreas.push(m)
    },

    toggleFamily(f: string) {
      const i = this.families.indexOf(f)
      if (i >= 0) this.families.splice(i, 1)
      else this.families.push(f)
    },

    clearFilters() {
      this.macroAreas = []
      this.families = []
      this.onlyReliable = false
      this.search = ''
      this.featureFilter = null
      this.growthMin = null
      this.growthMax = null
      this.wikiOnly = false
      this.minFeatures = null
      this.endangermentLevels = []
    },

    /**
     * 应用自然语言解析出的意图。
     *
     * 关键：**先清空再设置**，否则上一轮问的条件会残留下来，
     * 用户看到的结果与这次问的对不上。
     */
    applyIntent(intent: Record<string, unknown> | null) {
      this.clearFilters()
      if (!intent) return
      const known = new Set(this.familyList.map((f) => f.family))
      const areas = (intent.macroAreas as string[] | undefined) ?? []
      this.macroAreas = areas.filter((a) =>
        MACRO_AREAS.includes(a as MacroArea)) as MacroArea[]
      const fams = (intent.families as string[] | undefined) ?? []
      // 语系名要用真实值，模型可能给出近似的写法
      this.families = fams.filter((f) => known.has(f))
      this.search = (intent.nameQuery as string | undefined) ?? ''
      const fid = intent.featureId as string | undefined
      if (fid && this.matrix?.feature_ids.includes(fid)) {
        const raw = (intent.featureValue as string | undefined) ?? null
        // ⚠️ 矩阵里存的是 WALS 的**数值编码**（values.csv 的 Value 列，如 "2"），
        // 而自然语言与大模型给出的是**标签**（如 "SOV"）。不转换的话
        // 「语序是 SOV 的语言」会永远筛出 0 条 —— 这是个很容易漏的坑。
        let value: string | null = null
        if (raw != null) {
          const hit = (this.features?.codes ?? []).find((c) =>
            c.Parameter_ID === fid &&
            (c.Name === raw || c.Number === raw || c.ID === raw))
          value = hit ? hit.Number : raw
        }
        this.featureFilter = { featureId: fid, value }
        // 让「条件对比」面板也切到这个特征，两边保持一致
        this.compareFeature = fid
      }
      if (typeof intent.growthMin === 'number') this.growthMin = intent.growthMin
      if (typeof intent.growthMax === 'number') this.growthMax = intent.growthMax
      if (intent.wikiOnly) this.wikiOnly = true
      if (typeof intent.minFeatures === 'number') this.minFeatures = intent.minFeatures
      const lv = intent.endangermentLevels as number[] | undefined
      if (Array.isArray(lv)) {
        this.endangermentLevels = lv.filter((n) => n >= 1 && n <= 6)
      }
      const p = intent.period ? String(intent.period) : ''
      if (/^\d{4}$/.test(p)) {
        const i = this.months.findIndex((m) => m.startsWith(p))
        if (i >= 0) this.monthIndex = i
      } else if (/^\d{6}$/.test(p)) {
        const i = this.months.indexOf(p)
        if (i >= 0) this.monthIndex = i
      }
    },

    setCompareFeature(id: string | null) {
      this.compareFeature = id
      // 换特征时旧的分组筛选已无意义
      this.featureFilter = null
    },

    /** 点选分组：同一个分组再点一次取消 */
    toggleFeatureFilter(featureId: string, value: string) {
      const cur = this.featureFilter
      this.featureFilter = cur && cur.featureId === featureId && cur.value === value
        ? null
        : { featureId, value }
    },

    setMonthIndex(i: number) {
      this.monthIndex = Math.min(Math.max(i, 0), Math.max(0, this.months.length - 1))
    },

    select(id: string | null) {
      this.selected = this.selected === id ? null : id
    },

    toggleComparison(id: string) {
      const i = this.comparisonSet.indexOf(id)
      if (i >= 0) this.comparisonSet.splice(i, 1)
      else if (this.comparisonSet.length < 4) this.comparisonSet.push(id)
    },

    /**
     * 跳到故事模式的第 i 步；传 null 退出故事模式回到自由探索。
     *
     * 每一步只做两件事：把看板切到那个视图、设好那组筛选。
     * 因为走的还是同一套 store 字段，所以**故事与自由探索共享全部状态** ——
     * 退出故事后不会丢掉刚才看到的那组筛选，可以直接接着玩。
     */
    goStory(i: number | null) {
      if (i == null) {
        this.storyStep = null
        return
      }
      const idx = Math.min(Math.max(i, 0), STORY.length - 1)
      this.storyStep = idx
      STORY[idx].enter(this)
    },
  },
})
