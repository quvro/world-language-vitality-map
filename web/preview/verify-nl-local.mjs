/**
 * 端到端验证本地规则解析器：问题 → 意图 → 套用真实筛选逻辑 → 命中数。
 *
 * 这是没有 API Key 时的默认通路，所以必须单独验证它真的能筛出东西，
 * 而不是"能解析但筛出 0 条"。
 */
import { readFileSync } from 'node:fs'
import { describeIntent, parseLocal } from '../shared/intent.js'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const matrix = load('feature_matrix.json')
const features = load('features.json')
const zh = load('zh_labels.json')

const keyIndex = {}
matrix.language_keys.forEach((k, i) => { keyIndex[k] = i })
const featureCount = {}
matrix.language_keys.forEach((k, i) => {
  let n = 0
  for (let fi = 0; fi < matrix.values.length; fi++) if (matrix.values[fi][i] != null) n++
  featureCount[k] = n
})
const families = [...new Set(langs.map((l) => l.family).filter(Boolean))]
const featureName = (id) => features.features.find((f) => f.ID === id)?.Name ?? id

/** 复现 store 的筛选逻辑（含标签 → 数值编码的转换） */
function apply(intent) {
  let rows = langs.slice()
  if (intent.macroAreas?.length) rows = rows.filter((l) => intent.macroAreas.includes(l.macroarea))
  if (intent.families?.length) {
    const known = new Set(families)
    const fams = intent.families.filter((f) => known.has(f))
    if (fams.length) rows = rows.filter((l) => fams.includes(l.family))
  }
  if (intent.wikiOnly) rows = rows.filter((l) => l.wiki_code)
  if (intent.minFeatures != null) rows = rows.filter((l) => featureCount[l.wals_id] >= intent.minFeatures)
  if (intent.growthMin != null || intent.growthMax != null) {
    rows = rows.filter((l) => {
      if (!(l.baseline_ok && l.growth != null)) return false
      const g = l.growth * 100
      if (intent.growthMin != null && g < intent.growthMin) return false
      if (intent.growthMax != null && g > intent.growthMax) return false
      return true
    })
  }
  if (intent.featureId) {
    const fi = matrix.feature_ids.indexOf(intent.featureId)
    if (fi >= 0) {
      const row = matrix.values[fi]
      // 标签 -> 数值编码
      let rawValue = intent.featureValue ?? null
      if (rawValue != null) {
        const hit = features.codes.find((c) => c.Parameter_ID === intent.featureId &&
          (c.Name === rawValue || c.Number === rawValue || c.ID === rawValue))
        rawValue = hit ? hit.Number : rawValue
      }
      rows = rows.filter((l) => {
        const i = keyIndex[l.wals_id]
        if (i == null) return false
        return rawValue != null ? row[i] === rawValue : row[i] != null
      })
    }
  }
  return rows
}

const CASES = [
  '非洲语区里语序是 SOV 且在增长的语言',
  '印欧语系中有声调的语言',
  '有维基百科版本、数据完整、这十年在衰退的语言',
  '定位到 2018 年',
  '南岛语系有维基百科版本的语言',
  '语序是 VSO 的语言',
  '亚洲在衰退的语言',
  '有小舌辅音、数据完整的语言',
  'SOV languages in Africa that are growing',
  'Indo-European languages with tone',
  '南美洲的语言',
  '随便问一句没有条件的',
]

let fail = 0
for (const q of CASES) {
  const intent = parseLocal(q, { families, features: features.features.map((f) => `${f.ID} ${f.Name}`) })
  const chips = describeIntent(intent, 'zh', featureName)
  const rows = apply(intent)
  const wiki = rows.filter((l) => l.wiki_code).length
  const conds = Object.keys(intent).filter((k) => k !== '_source' && k !== 'explanation')
  // period 只是把时间轴定位过去，不筛行；但它也是有效意图
  const onlyPeriod = conds.length === 1 && conds[0] === 'period'
  const noCond = conds.length === 0
  let verdict
  if (noCond) verdict = 'NONE'          // 本来就没条件（预期行为）
  else if (rows.length === 0 && !onlyPeriod) verdict = 'ZERO'  // 有条件下却筛空了（要查）
  else verdict = 'OK  '
  if (verdict === 'ZERO') fail++
  console.log(`\n[${verdict}] ${q}`)
  console.log(`      条件: ${chips.map((c) => `${c.label}=${c.value}`).join(' | ') || '(没识别出条件)'}`)
  console.log(`      命中: ${rows.length} 门, 其中有维基 ${wiki} 门`)
  if (intent.period) console.log(`      时间定位: ${intent.period}`)
}

console.log(`\n========================================`)
console.log(`筛空（ZERO）的用例 = ${fail} 个（应为 0）`)
process.exit(fail === 0 ? 0 : 1)
