/**
 * 在 Node 里复现预览页的数据处理逻辑，提前暴露运行时错误。
 * 只验证数据变换，不验证绘图（本机没有可用的无头浏览器）。
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const fmt = (n) => n.toLocaleString('en-US')

const langs = load('languages.json')
const matrix = load('feature_matrix.json')
const featDefs = load('features.json')

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  ' + extra : ''}`)
}

/* ---- KPI ---- */
const withCoords = langs.filter((l) => l.latitude && l.longitude)
const withWiki = langs.filter((l) => l.wiki_code)
const reliable = langs.filter((l) => l.baseline_ok && l.growth != null)
check('languages.json 非空', langs.length > 3000, `${langs.length} 条`)
check('有坐标的点位', withCoords.length > 2000, `${withCoords.length}`)
check('关联维基的语言', withWiki.length > 200, `${withWiki.length}`)
check('可用于增长分析', reliable.length > 150, `${reliable.length}`)
check('坐标均为有限数',
  withCoords.every((l) => Number.isFinite(+l.longitude) && Number.isFinite(+l.latitude)))

/* ---- 世界散点：语区分组 ---- */
const MACRO = ['Africa', 'Eurasia', 'Papunesia', 'North America',
               'South America', 'Australia']
const groups = MACRO.map((m) => ({
  m, n: withCoords.filter((l) => l.macroarea === m).length,
}))
check('六大语区都有点位', groups.every((g) => g.n > 0),
  groups.map((g) => `${g.m}=${g.n}`).join(' '))
const ungrouped = withCoords.filter((l) => !MACRO.includes(l.macroarea)).length
check('无落在六区之外的点（可全部着色）', ungrouped === 0,
  ungrouped ? `${ungrouped} 个未着色` : '')

/* ---- 增长条形图 ---- */
const ranked = reliable.slice().sort((a, b) => a.growth - b.growth)
const picked = [...ranked.slice(0, 8), ...ranked.slice(-8)]
check('增长榜取满 16 条', picked.length === 16)
check('增长值均为有限数', picked.every((l) => Number.isFinite(l.growth * 100)))
check('含负增长与正增长',
  picked.some((l) => l.growth < 0) && picked.some((l) => l.growth > 0))
check('基线/近期值可用于 tooltip',
  picked.every((l) => Number.isFinite(l.views_baseline) && Number.isFinite(l.views_recent)))
console.log(`       最跌: ${ranked[0].name} ${(ranked[0].growth * 100).toFixed(1)}%`)
console.log(`       最涨: ${ranked[ranked.length - 1].name} ` +
  `${(ranked[ranked.length - 1].growth * 100).toFixed(1)}%`)

/* ---- 特征覆盖率 ---- */
check('feature_ids 与 values 行数一致',
  matrix.feature_ids.length === matrix.values.length,
  `${matrix.feature_ids.length}`)
check('每行长度与 language_keys 一致',
  matrix.values.every((row) => row.length === matrix.language_keys.length))
const cov = matrix.feature_ids.map((fid, i) => ({
  fid, n: matrix.values[i].reduce((a, v) => a + (v == null ? 0 : 1), 0),
}))
const nameOf = Object.fromEntries(featDefs.features.map((f) => [f.ID, f.Name]))
const top = cov.slice().sort((a, b) => b.n - a.n).slice(0, 18).reverse()
check('Top18 特征都能取到名字', top.every((d) => !!nameOf[d.fid]),
  top.filter((d) => !nameOf[d.fid]).map((d) => d.fid).join(',') || '')
check('覆盖率数值合理（1..3000）', cov.every((d) => d.n >= 0 && d.n <= 3000))
console.log(`       覆盖率中位数: ${cov.map((d) => d.n).sort((a, b) => a - b)[95]}`)
console.log(`       最高: ${nameOf[top[17].fid]} = ${fmt(top[17].n)}`)

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
