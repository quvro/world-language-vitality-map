/** 与 data/processed/*.json 的实际结构一一对应。 */

export interface Language {
  wals_id: string
  glottocode: string | null
  name: string
  macroarea: string | null
  latitude: number | null
  longitude: number | null
  family: string | null
  subfamily: string | null
  genus: string | null
  iso639p3: string | null
  country_id: string | null
  /** 关联到的维基语言版本码；没有则为 null */
  wiki_code: string | null

  // 以下字段由 03_build_dataset.py 的活力计算写入，仅对有维基的语言存在
  month_first?: string
  views_first?: number
  month_last?: string
  views_last?: number
  /** 首 3 个月的月均浏览量（基线） */
  views_baseline?: number
  /** 末 3 个月的月均浏览量 */
  views_recent?: number
  /** 基线是否足够高，false 表示增长率不可信（统计伪影） */
  baseline_ok?: boolean
  /** (recent - baseline) / baseline */
  growth?: number
}

export interface Timeseries {
  metrics: ['views', 'edits']
  by_language: Record<string, {
    views: Record<string, number>
    edits: Record<string, number>
  }>
}

export interface FeatureDef {
  ID: string
  Name: string
  Description: string
  ColumnSpec: string
  Chapter_ID: string
}

export interface CodeDef {
  ID: string
  Parameter_ID: string
  Name: string
  Description: string
  Number: string
  icon: string
}

export interface Features {
  features: FeatureDef[]
  codes: CodeDef[]
}

export interface FeatureMatrix {
  language_keys: string[]
  feature_ids: string[]
  /** 列式存储：values[i] 对应 feature_ids[i]，长度等于 language_keys */
  values: (string | null)[][]
}

/** 六大语区，用于着色与筛选（与地图图例一致） */
export const MACRO_AREAS = [
  'Africa',
  'Eurasia',
  'Papunesia',
  'North America',
  'South America',
  'Australia',
] as const

export type MacroArea = (typeof MACRO_AREAS)[number]
