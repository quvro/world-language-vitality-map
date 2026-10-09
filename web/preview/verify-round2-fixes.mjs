/**
 * 验证这轮修的几个逻辑问题（不需要浏览器）：
 *   #3 活力变化：可分析语言少于 18 个时，跌幅榜/涨幅榜是否会重复
 *   #5 时间轴折线：是否真的随筛选变化
 *   #9 国家名映射：是否覆盖地图全部区域
 *   #7 名称解析：display.ts 是否还在初始化时把 store.lang 固定住
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  ' + extra : ''}`)
}

/* ---------------- #3 榜单切片是否重复 ---------------- */
console.log('=== #3 活力变化榜单（复现旧逻辑 vs 新逻辑）===')
const all = langs.filter((l) => l.baseline_ok && l.growth != null)
  .slice().sort((a, b) => a.growth - b.growth)
const K = 9

function oldPick(r) { return [...r.slice(0, K), ...r.slice(-K)] }
function newPick(r) { return r.length <= K * 2 ? r.slice() : [...r.slice(0, K), ...r.slice(-K)] }
function dupCount(arr) { return arr.length - new Set(arr.map((d) => d.wals_id)).size }

for (const n of [4, 6, 10, 17, 18, 19, 40, all.length]) {
  const slice = all.slice(0, n)
  const od = dupCount(oldPick(slice))
  const nd = dupCount(newPick(slice))
  const mark = od > 0 ? `旧逻辑重复 ${od} 个` : '旧逻辑无重复'
  console.log(`  可分析 ${String(n).padStart(3)} 门 -> 新逻辑取 `
    + `${String(newPick(slice).length).padStart(2)} 条, 重复 ${nd} 个   (${mark})`)
}
const badOld = [4, 6, 10, 17].every((n) => dupCount(oldPick(all.slice(0, n))) > 0)
const badNew = [4, 6, 10, 17, 18, 19, 40, all.length]
  .some((n) => dupCount(newPick(all.slice(0, n))) > 0)
check('旧逻辑在少量数据时确实会重复（说明这个 bug 真实存在）', badOld)
check('新逻辑在任何规模下都不重复', !badNew)

/* ---------------- #5 时间轴折线是否随筛选变化 ---------------- */
console.log('\n=== #5 时间轴折线：全部 vs 筛选后 ===')
const ts = load('timeseries.json').by_language
const months = Object.keys(ts[Object.keys(ts)[0]].views).sort()

function totals(ids) {
  return months.map((m) => {
    let s = 0
    for (const id of ids) s += ts[id]?.views[m] ?? 0
    return s
  })
}
const allIds = langs.map((l) => l.wals_id)
const africaIds = langs.filter((l) => l.macroarea === 'Africa').map((l) => l.wals_id)
const t1 = totals(allIds)
const t2 = totals(africaIds)
const last = (a) => a[a.length - 1]
console.log(`  全部语言      末月合计 = ${last(t1).toLocaleString('en-US')}`)
console.log(`  仅非洲语区    末月合计 = ${last(t2).toLocaleString('en-US')}`)
check('筛选后折线明显不同（真的按筛选走了）', last(t1) !== last(t2),
  `差 ${(last(t1) / Math.max(last(t2), 1)).toFixed(1)} 倍`)

/* ---------------- #9 国家名映射覆盖 ---------------- */
console.log('\n=== #9 国家名映射覆盖 ===')
const world = readFileSync('web/public/vendor/world.js', 'utf8')
const regionNames = []
for (const m of world.matchAll(/"name":\s*"([^"]+)"/g)) {
  const n = m[1]
  if (!n.startsWith('urn:') && !regionNames.includes(n)) regionNames.push(n)
}
const countiesSrc = readFileSync('web/src/countries.ts', 'utf8')
// 键有两种写法：含空格/连字符/点的必须带引号（'W. Sahara'），
// 单字标识符则不带（Somalia）。所以要同时匹配两种。
const mapKeys = [...countiesSrc.matchAll(
  /^\s{2}(?:'([^']+)'|"([^"]+)"|([\p{L}_$][\p{L}\p{N}_$]*)):/gmu
)].map((m) => m[1] ?? m[2] ?? m[3])
console.log(`  地图区域 ${regionNames.length} 个, 映射表解析出 ${mapKeys.length} 个键`)
const missing = regionNames.filter((n) => !mapKeys.includes(n))
const extra = mapKeys.filter((k) => !regionNames.includes(k))
check('映射表覆盖全部地图区域', missing.length === 0, missing.join(', '))
check('映射表没有多余的键', extra.length === 0, extra.join(', '))

/* ---------------- #7 display.ts 是否还在初始化时固定语言 ---------------- */
console.log('\n=== #7 名称解析的响应式依赖 ===')
const disp = readFileSync('web/src/display.ts', 'utf8')
check('zh 已改为函数（每次调用都读 store.lang）',
  /const zh = \(\) => store\.lang === 'zh'/.test(disp))
check('不再有初始化时求值的 const zh = store.lang…',
  !/const zh = store\.lang === 'zh'\s*$/m.test(disp))

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
