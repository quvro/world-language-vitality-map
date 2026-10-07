/** 验证中文名解析：与前端 display.ts 的逻辑一致。 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const zh = load('zh_labels.json')

function zhName(l) {
  const byIso = l.iso639p3 ? zh.by_iso639p3[l.iso639p3.toLowerCase()] : undefined
  const byG = l.glottocode ? zh.by_glottocode[l.glottocode] : undefined
  return byIso || byG || null
}

const named = langs.filter(zhName)
console.log(`全部语言 ${langs.length}，有中文名 ${named.length} (${(named.length / langs.length * 100).toFixed(0)}%)`)
const wiki = langs.filter((l) => l.wiki_code)
const wikiNamed = wiki.filter(zhName)
console.log(`有维基版本 ${wiki.length}，有中文名 ${wikiNamed.length} (${(wikiNamed.length / wiki.length * 100).toFixed(0)}%)`)

console.log('\n=== 有维基版本的语言：中文名样例 ===')
for (const l of wikiNamed.filter((x) => x.views_baseline > 1e7).slice(0, 12)) {
  const tail = l.name !== zhName(l) ? `  (${l.name})` : ''
  console.log(`  ${zhName(l)}${tail}`)
}

console.log('\n=== 未拿到中文名的（回退英文）===')
const missing = wiki.filter((l) => !zhName(l))
for (const l of missing.slice(0, 8)) console.log(`  ${l.name}  iso=${l.iso639p3 ?? '—'} glotto=${l.glottocode ?? '—'}`)

console.log('\n=== 语系中文名映射覆盖 ===')
const fams = [...new Set(langs.map((l) => l.family).filter(Boolean))]
const map = zh.family
const hit = fams.filter((f) => map[f])
const byCount = {}
for (const l of langs) if (l.family) byCount[l.family] = (byCount[l.family] || 0) + 1
const total = langs.filter((l) => l.family).length
const covered = fams.filter((f) => map[f]).reduce((a, f) => a + byCount[f], 0)
console.log(`  语系种类 ${fams.length}，有中文名 ${hit.length}`)
console.log(`  按语言数加权覆盖 = ${(covered / total * 100).toFixed(1)}%`)
console.log('  未映射的语系（按语言数）:')
for (const [f, n] of Object.entries(byCount).sort((a, b) => b[1] - a[1]).slice(0, 10)) {
  if (!map[f]) console.log(`    ${f}  ${n} 门`)
}
