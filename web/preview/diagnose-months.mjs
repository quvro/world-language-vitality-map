/**
 * 诊断：为什么拖时间轴时地图上的点没反应？
 *
 * 怀疑点：store 的 months getter 用了
 *     Object.values(by_language)[0]
 * 只取「第一个语言」的月份键。如果那门语言的月份覆盖不完整，
 * 时间轴能走的月份就是残缺的，拖到某些下标时绝大多数语言在当月没有值，
 * 于是地图上的点不会变化（甚至消失）。
 */
import { readFileSync } from 'node:fs'

const ts = JSON.parse(readFileSync('data/processed/timeseries.json', 'utf8'))
const byLang = ts.by_language
const keys = Object.keys(byLang)
console.log(`语言数 = ${keys.length}`)

const first = keys[0]
const firstMonths = Object.keys(byLang[first].views).sort()
console.log(`\n第一个语言 = ${first}`)
console.log(`  它的月份数 = ${firstMonths.length}`)
console.log(`  区间 = ${firstMonths[0]} .. ${firstMonths[firstMonths.length - 1]}`)

// 所有语言的月份并集
const union = new Set()
for (const k of keys) for (const m of Object.keys(byLang[k].views)) union.add(m)
const unionSorted = [...union].sort()
console.log(`\n全部语言月份并集 = ${unionSorted.length}`)
console.log(`  区间 = ${unionSorted[0]} .. ${unionSorted[unionSorted.length - 1]}`)

const missing = unionSorted.filter((m) => !firstMonths.includes(m))
console.log(`\n并集里有、但第一个语言没有的月份 = ${missing.length}`)
if (missing.length) {
  console.log(`  例如: ${missing.slice(0, 12).join(', ')}${missing.length > 12 ? ' …' : ''}`)
}

// 每门语言的月份数分布
const counts = keys.map((k) => Object.keys(byLang[k].views).length).sort((a, b) => a - b)
const q = (p) => counts[Math.floor((counts.length - 1) * p)]
console.log(`\n每门语言的月份数: 最少 ${counts[0]}, 25% ${q(0.25)}, ` +
  `中位 ${q(0.5)}, 75% ${q(0.75)}, 最多 ${counts[counts.length - 1]}`)
console.log(`月份数 < 127 的语言 = ${counts.filter((c) => c < 127).length}`)

// 模拟：用「第一个语言的月份」当时间轴 vs 用「并集」
function coverage(monthList, idx) {
  const m = monthList[idx]
  let n = 0
  for (const k of keys) if (byLang[k].views[m] != null) n++
  return { month: m, langs: n }
}

console.log('\n=== 模拟拖时间轴：用「第一个语言的月份」(当前实现) ===')
const step = Math.max(1, Math.floor(firstMonths.length / 8))
for (let i = 0; i < firstMonths.length; i += step) {
  const c = coverage(firstMonths, i)
  console.log(`  idx=${String(i).padStart(3)}  ${c.month}  当月有值的语言 = ${c.langs}`)
}

console.log('\n=== 对照：用「并集月份」 ===')
const step2 = Math.max(1, Math.floor(unionSorted.length / 8))
for (let i = 0; i < unionSorted.length; i += step2) {
  const c = coverage(unionSorted, i)
  console.log(`  idx=${String(i).padStart(3)}  ${c.month}  当月有值的语言 = ${c.langs}`)
}
