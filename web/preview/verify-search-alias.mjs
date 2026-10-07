/**
 * 验证：搜「中文」「普通话」能不能找到 Mandarin？
 * 复现 store.filteredBase 的搜索逻辑 + terms.ts 的别名表。
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const zh = load('zh_labels.json')

// 从 terms.ts 里抽出 SEARCH_ALIASES（避免为了一个测试把 TS 编译进来）
const src = readFileSync('web/src/terms.ts', 'utf8')
const block = src.slice(src.indexOf('export const SEARCH_ALIASES'))
const aliases = {}
for (const m of block.matchAll(/^\s{2}([a-z]{2,3}):\s*\[([^\]]*)\]/gm)) {
  aliases[m[1]] = m[2].split(',').map((s) => s.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean)
}
console.log(`别名表：${Object.keys(aliases).length} 条`)
console.log(`  cmn -> ${JSON.stringify(aliases.cmn)}`)

function searchText(l) {
  const iso = (l.iso639p3 || '').toLowerCase()
  const parts = [l.name]
  const cn = (iso && zh.by_iso639p3[iso]) || (l.glottocode && zh.by_glottocode[l.glottocode])
  if (cn) parts.push(cn)
  if (iso) {
    parts.push(iso)
    if (aliases[iso]) parts.push(...aliases[iso])
  }
  if (l.wiki_code) parts.push(l.wiki_code)
  return parts.join(' ').toLowerCase()
}

const QUERIES = ['中文', '普通话', '汉语', '官话', 'mandarin', 'chinese',
  '粤语', 'cantonese', '阿拉伯语', '波斯语', '斯瓦希里语', '乌兹别克语',
  '德语', 'german', '日语', '广州话']

console.log('\n=== 搜索结果 ===')
for (const q of QUERIES) {
  const ql = q.toLowerCase()
  const hits = langs.filter((l) => searchText(l).includes(ql))
  const names = hits.slice(0, 3).map((l) => {
    const iso = (l.iso639p3 || '').toLowerCase()
    const cn = (iso && zh.by_iso639p3[iso]) || (l.glottocode && zh.by_glottocode[l.glottocode])
    return cn ? `${cn}/${l.name}` : l.name
  })
  const mark = hits.length ? '' : '   <-- 搜不到'
  console.log(`  ${q.padEnd(12)} 命中 ${String(hits.length).padStart(4)}  ${names.join('、')}${mark}`)
}

console.log('\n=== 汉语族语言在数据里的状态 ===')
const HAN = ['cmn', 'yue', 'wuu', 'hak', 'nan', 'gan', 'hsn', 'cjy']
for (const iso of HAN) {
  const l = langs.find((x) => (x.iso639p3 || '').toLowerCase() === iso)
  if (!l) { console.log(`  ${iso}: WALS 里没有`); continue }
  const cn = zh.by_iso639p3[iso] || '—'
  console.log(`  ${iso.padEnd(5)} ${l.name.padEnd(16)} 中文=${cn.padEnd(8)} ` +
    `wiki=${(l.wiki_code || '—').padEnd(5)} 坐标=${l.latitude ? 'Y' : 'N'} ` +
    `趋势=${l.growth != null ? (l.growth * 100).toFixed(0) + '%' : '—'}`)
}
