/**
 * 调查两件事：
 *  A. 中文/普通话在地图上的处境 —— 是数据缺失，还是 macrolanguage 的包含关系？
 *  B. 条件对比里哪些特征与取值名需要翻译（按分组差异排序）
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const zh = load('zh_labels.json')
const M = load('feature_matrix.json')
const F = load('features.json')

const zhName = (l) =>
  (l.iso639p3 && zh.by_iso639p3[l.iso639p3.toLowerCase()]) ||
  (l.glottocode && zh.by_glottocode[l.glottocode]) || null

console.log('===== A. 汉语相关条目 =====')
const KEY = /mandarin|chinese|cantonese|wu |hakka|min |xiang|gan |mand\b|yue|wuu|nan|hak|gan /i
const hits = langs.filter((l) => KEY.test(l.name) || /^(cmn|zho|yue|wuu|nan|hak|gan|czh|cjy|mnp|lzh)$/.test(l.iso639p3 || ''))
for (const l of hits) {
  console.log(`  ${l.name.padEnd(30)} 中文=${(zhName(l) || '—').padEnd(10)} ` +
    `iso=${String(l.iso639p3 || '—').padEnd(5)} glotto=${String(l.glottocode || '—').padEnd(10)} ` +
    `coord=${l.latitude ? 'Y' : 'N'} wiki=${l.wiki_code || '—'}`)
}

console.log('\n--- zh.wikipedia 关联到了哪一条？---')
const zhLinked = langs.filter((l) => l.wiki_code === 'zh')
for (const l of zhLinked) {
  console.log(`  ${l.name}  中文名=${zhName(l) || '—'}  glotto=${l.glottocode}  iso=${l.iso639p3}`)
  console.log(`    坐标 = ${l.latitude}, ${l.longitude}`)
  console.log(`    十年趋势 = ${l.growth != null ? (l.growth * 100).toFixed(1) + '%' : '—'}  ` +
    `基线可靠 = ${l.baseline_ok}`)
}

console.log('\n--- 共享同一个 Glottocode 的汉语条目（macrolanguage 包含关系）---')
const byGlotto = new Map()
for (const l of langs) {
  if (!l.glottocode) continue
  if (!byGlotto.has(l.glottocode)) byGlotto.set(l.glottocode, [])
  byGlotto.get(l.glottocode).push(l)
}
// 找出与汉语相关的 glottocode 组
const chineseGlottos = new Set(hits.map((l) => l.glottocode).filter(Boolean))
for (const g of chineseGlottos) {
  const grp = byGlotto.get(g) || []
  if (grp.length > 1) {
    console.log(`  glottocode=${g}`)
    for (const l of grp) console.log(`     ${l.name}`)
  }
}

console.log('\n--- 汉藏语系下有多少条、多少有坐标/维基 ---')
const st = langs.filter((l) => l.family === 'Sino-Tibetan')
console.log(`  汉藏语系条目 = ${st.length}`)
console.log(`  其中有坐标   = ${st.filter((l) => l.latitude).length}`)
console.log(`  其中有维基   = ${st.filter((l) => l.wiki_code).length}`)
console.log(`  其中在 macroarea=Eurasia = ${st.filter((l) => l.macroarea === 'Eurasia').length}`)

console.log('\n===== B. 条件对比需要翻译的内容 =====')
const idx = new Map()
M.language_keys.forEach((k, i) => idx.set(k, i))
const MIN = 12
const codeLabel = new Map()
for (const c of F.codes) codeLabel.set(`${c.Parameter_ID}\u0000${c.Number}`, c.Name)
const nameOf = new Map(F.features.map((f) => [f.ID, f.Name]))

const hasWiki = new Map(langs.map((l) => [l.wals_id, !!l.wiki_code]))
const scored = []
for (let fi = 0; fi < M.feature_ids.length; fi++) {
  const fid = M.feature_ids[fi]
  const row = M.values[fi]
  const acc = new Map()
  let n = 0
  for (let j = 0; j < M.language_keys.length; j++) {
    const v = row[j]
    if (v == null) continue
    n++
    let a = acc.get(v)
    if (!a) { a = { t: 0, w: 0 }; acc.set(v, a) }
    a.t++
    if (hasWiki.get(M.language_keys[j])) a.w++
  }
  const codes = []
  for (const [val, a] of acc) {
    if (a.t >= MIN) codes.push({ val, label: codeLabel.get(`${fid}\u0000${val}`) || val, t: a.t, rate: a.w / a.t })
  }
  if (codes.length < 2) continue
  const rates = codes.map((c) => c.rate)
  const spread = Math.max(...rates) - Math.min(...rates)
  scored.push({ fid, name: nameOf.get(fid) || fid, n, spread, codes })
}
scored.sort((a, b) => b.spread - a.spread)

console.log(`\n特征总数 ${M.feature_ids.length}，可对比 ${scored.length}`)
console.log('\n--- 分组差异 Top 15 特征（含取值名，这些是要翻译的）---')
for (const s of scored.slice(0, 15)) {
  console.log(`\n  [${s.fid}] ${s.name}   覆盖率 ${s.n}  极差 ${(s.spread * 100).toFixed(0)}pp`)
  for (const c of s.codes.slice(0, 6)) {
    console.log(`        ${String(c.label).padEnd(34)} ${String(c.t).padStart(4)} 门  ${(c.rate * 100).toFixed(0)}%`)
  }
}

const topN = 25
const codesNeeded = new Set()
for (const s of scored.slice(0, topN)) for (const c of s.codes) codesNeeded.add(`${s.fid}\u0000${c.label}`)
console.log(`\n--- 翻译工作量估算 ---`)
console.log(`  特征名（全部）      = ${M.feature_ids.length}`)
console.log(`  前 ${topN} 特征的取值名 = ${codesNeeded.size}`)
console.log(`  全部取值名          = ${F.codes.length}`)
