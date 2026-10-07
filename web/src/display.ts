/**
 * 显示名称解析。
 *
 * 语言名来自 WALS，是英文。中文名从 Wikidata 抓（pipeline/04_fetch_zh_labels.py），
 * 落在 data/processed/zh_labels.json，由 store 加载。
 *
 * 语区只有 6 个、常用语系也就几十个，机器来源反而不方便，直接内联。
 */
import { useDataset } from '@/stores/dataset'
import type { Language } from '@/types'
import { CODE_ZH, FEATURE_ZH, MACRO_ZH, SEARCH_ALIASES } from '@/terms'

export { MACRO_ZH }

export const FAMILY_ZH: Record<string, string> = {
  'Niger-Congo': '尼日尔-刚果语系',
  Austronesian: '南岛语系',
  'Indo-European': '印欧语系',
  'Sino-Tibetan': '汉藏语系',
  'Afro-Asiatic': '亚非语系',
  'Pama-Nyungan': '帕马-尼永干语系',
  'Trans-New Guinea': '跨新几内亚语系',
  'Oto-Manguean': '奥托-曼格语系',
  Altaic: '阿尔泰语系',
  'Austro-Asiatic': '南亚语系',
  'Eastern Sudanic': '东苏丹语系',
  'Uto-Aztecan': '犹他-阿兹特克语系',
  Algic: '阿尔冈昆语系',
  Uralic: '乌拉尔语系',
  Dravidian: '达罗毗荼语系',
  'Tai-Kadai': '侗台语系',
  'Hmong-Mien': '苗瑶语系',
  Tupi: '图皮语系',
  Carib: '加勒比语系',
  Arawakan: '阿拉瓦克语系',
  Quechuan: '克丘亚语系',
  Mayan: '玛雅语系',
  Turkic: '突厥语系',
  Mongolic: '蒙古语系',
  Tungusic: '通古斯语系',
  Japanese: '日语系',
  Korean: '朝鲜语系',
  Kartvelian: '卡特维尔语系',
  'Northwest Caucasian': '西北高加索语系',
  'Northeast Caucasian': '东北高加索语系',
  Basque: '巴斯克语系',
  'Eskimo-Aleut': '爱斯基摩-阿留申语系',
  'Na-Dene': '纳-德内语系',
  Salishan: '萨利什语系',
  Siouan: '苏语系',
  Iroquoian: '易洛魁语系',
  Muskogean: '马斯科吉语系',
  Athapaskan: '阿萨帕斯卡语系',
  'Nilo-Saharan': '尼罗-撒哈拉语系',
  'Chukotko-Kamchatkan': '楚科奇-堪察加语系',
  'Creole': '克里奥尔语',
  other: '其他',
  '(未分类)': '未分类',
}

/** 统一的名称解析入口。语言名回退顺序：中文名 → 英文名。 */
export function useDisplayNames() {
  const store = useDataset()

  const zh = store.lang === 'zh'

  const macro = (m: string | null | undefined): string => {
    if (!m) return '—'
    return zh ? (MACRO_ZH[m] ?? m) : m
  }

  const family = (f: string | null | undefined): string => {
    const key = f || '(未分类)'
    return zh ? (FAMILY_ZH[key] ?? FAMILY_ZH[f ?? ''] ?? key) : key
  }

  const language = (l: Pick<Language, 'name' | 'iso639p3' | 'glottocode'>): string => {
    if (!zh) return l.name
    const dict = store.zhLabels
    if (!dict) return l.name
    const byIso = l.iso639p3 ? dict.by_iso639p3[l.iso639p3.toLowerCase()] : undefined
    const byGlotto = l.glottocode ? dict.by_glottocode[l.glottocode] : undefined
    return byIso || byGlotto || l.name
  }

  /** 语法特征的中文名；没有译名时回退英文（WALS 无官方中文版） */
  const feature = (id: string, fallback: string): string =>
    zh ? (FEATURE_ZH[id] ?? fallback) : fallback

  /** 特征取值的中文名；只翻译了有把握的那些，其余回退英文 */
  const code = (label: string): string => (zh ? (CODE_ZH[label] ?? label) : label)

  /**
   * 语言的可搜索文本。
   * 除中英名外还接入别名表 —— 否则搜「中文」「普通话」找不到 Mandarin
   * （它在 Wikidata 的中文标签是「官话」）。
   */
  const searchText = (
    l: Pick<Language, 'name' | 'iso639p3' | 'glottocode' | 'wiki_code'>
  ): string => {
    const parts = [l.name]
    const cn = language(l)
    if (cn) parts.push(cn)
    const iso = (l.iso639p3 || '').toLowerCase()
    if (iso) {
      parts.push(iso)
      const alias = SEARCH_ALIASES[iso]
      if (alias) parts.push(...alias)
    }
    if (l.wiki_code) parts.push(l.wiki_code)
    return parts.join(' ').toLowerCase()
  }

  return { macro, family, language, feature, code, searchText }
}
