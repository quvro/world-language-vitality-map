/**
 * 验证「条件对比」到底有没有信号。
 *
 * 如果各组（如 SOV / SVO / VSO）的数字在场率差不多，那这个交互就是空的。
 * 这里用真实数据算出每个特征的分组差异，并找出差异最大的特征 ——
 * 顺便决定默认应该展示哪个特征。
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const matrix = load('feature_matrix.json')
const features = load('features.json')

const idx = new Map()
matrix.language_keys.forEach((k, i) => idx.set(k, i))

const byId = new Map(features.features.map((f) => [f.ID, f.Name]))
// (Parameter_ID, Number) -> 取值名
const codeLabel = new Map()
for (const c of features.codes) codeLabel.set(`${c.Parameter_ID}\u0000${c.Number}`, c.Name)

const MIN_GROUP = 12

function groupsFor(fid) {
  const fi = matrix.feature_ids.indexOf(fid)
  if (fi < 0) return []
  const row = matrix.values[fi]
  const acc = new Map()
  for (const l of langs) {
    const i = idx.get(l.wals_id)
    if (i == null) continue
    const v = row[i]
    if (v == null) continue
    let a = acc.get(v)
    if (!a) { a = { total: 0, wiki: 0, g: [] }; acc.set(v, a) }
    a.total++
    if (l.wiki_code) a.wiki++
    if (l.baseline_ok && l.growth != null) a.g.push(l.growth * 100)
  }
  const out = []
  for (const [value, a] of acc) {
    if (a.total < MIN_GROUP) continue
    const g = a.g.slice().sort((x, y) => x - y)
    out.push({
      value,
      label: codeLabel.get(`${fid}\u0000${value}`) || value,
      total: a.total,
      wikiRate: a.wiki / a.total,
      median: g.length ? g[Math.floor(g.length / 2)] : null,
      n: g.length,
    })
  }
  return out
}

const overallWiki = langs.filter((l) => l.wiki_code).length / langs.length
console.log(`整体数字在场率 = ${(overallWiki * 100).toFixed(1)}%  ` +
  `(${langs.filter((l) => l.wiki_code).length} / ${langs.length})`)

// 遍历所有特征，找分组差异最大的
const scored = []
for (const fid of matrix.feature_ids) {
  const gs = groupsFor(fid)
  if (gs.length < 2) continue
  const rates = gs.map((g) => g.wikiRate)
  const spread = Math.max(...rates) - Math.min(...rates)
  scored.push({ fid, name: byId.get(fid) || fid, n: gs.length, spread, gs })
}
scored.sort((a, b) => b.spread - a.spread)

console.log(`\n可对比的特征（>=2 个分组）= ${scored.length} / ${matrix.feature_ids.length}`)
console.log('\n=== 分组差异最大的 10 个特征 ===')
for (const s of scored.slice(0, 10)) {
  console.log(`  ${(s.spread * 100).toFixed(0).padStart(3)} 个百分点  ` +
    `${s.name}  (${s.fid}, ${s.n} 组)`)
}

console.log('\n=== 差异最大的特征展开 ===')
const top = scored[0]
console.log(`  ${top.name} (${top.fid})`)
for (const g of top.gs.sort((a, b) => b.wikiRate - a.wikiRate)) {
  const med = g.median == null ? '—' : `${g.median >= 0 ? '+' : ''}${g.median.toFixed(0)}%`
  console.log(`    ${g.label.padEnd(34)} ${String(g.total).padStart(5)} 门  ` +
    `在场率 ${(g.wikiRate * 100).toFixed(0).padStart(3)}%  趋势中位 ${med}`)
}

console.log('\n=== 默认候选：语序 Order of Subject, Object and Verb (81A) ===')
const sov = groupsFor('81A')
if (!sov.length) console.log('  (无足够分组)')
for (const g of sov.sort((a, b) => b.wikiRate - a.wikiRate)) {
  const med = g.median == null ? '—' : `${g.median >= 0 ? '+' : ''}${g.median.toFixed(0)}%`
  console.log(`    ${g.label.padEnd(34)} ${String(g.total).padStart(5)} 门  ` +
    `在场率 ${(g.wikiRate * 100).toFixed(0).padStart(3)}%  趋势中位 ${med}`)
}

const spread81 = sov.length ? Math.max(...sov.map((g) => g.wikiRate)) - Math.min(...sov.map((g) => g.wikiRate)) : 0
console.log(`\n  81A 的在场率极差 = ${(spread81 * 100).toFixed(0)} 个百分点`)

console.log('\n========================================')
if (scored.length > 20 && scored[0].spread > 0.15) {
  console.log(`结论：有信号。${scored.length} 个特征可对比，最大极差 ` +
    `${(scored[0].spread * 100).toFixed(0)} 个百分点`)
} else {
  console.log('结论：信号不足，这个交互需要重新设计')
  process.exitCode = 1
}
