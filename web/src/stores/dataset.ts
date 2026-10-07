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
import type {
  FeatureMatrix, Features, Language, MacroArea, Timeseries,
} from '@/types'

const DATA = '/data/processed/'

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
  loading: boolean
  error: string | null

  /** 语区筛选；空集表示不过滤 */
  macroAreas: MacroArea[]
  /** 语系筛选；空集表示不过滤 */
  families: string[]
  /** 只显示基线可靠（增长率可信）的语言 */
  onlyReliable: boolean
  search: string

  /** 主视图：地图 / 增长 / 特征 */
  activeView: 'map' | 'growth' | 'features'
  /** 地图模式：按语区分布 / 按当月活力 */
  mapMode: 'distribution' | 'vitality'

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
    loading: true,
    error: null,
    macroAreas: [],
    families: [],
    onlyReliable: false,
    search: '',
    activeView: 'map',
    mapMode: 'distribution',
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

    filtered(state): Language[] {
      const q = state.search.trim().toLowerCase()
      return state.langs.filter((l) => {
        if (state.macroAreas.length && !state.macroAreas.includes(l.macroarea as MacroArea)) {
          return false
        }
        if (state.families.length && !state.families.includes(l.family || '(未分类)')) {
          return false
        }
        if (state.onlyReliable && !(l.baseline_ok && l.growth != null)) return false
        if (q && !l.name.toLowerCase().includes(q)) return false
        return true
      })
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
  },
})
