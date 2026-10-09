/**
 * 验证 FeatureMatrix.vue 里的核心计算，与 Python 探查结果对照。
 * 主要防一件事：把统计逻辑从 Python 搬到 JS 时悄悄搬错。
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const matrix = load('feature_matrix.json')

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

// 复现 store.featureCount
const featureCount = {}
matrix.language_keys.forEach((k, i) => {
  let n = 0
  for (let fi = 0; fi < matrix.values.length; fi++) if (matrix.values[fi][i] != null) n++
  featureCount[k] = n
})

/* ---------------- 双重缺席（与组件同口径：只算真语言）---------------- */
console.log('=== 双重缺席分桶 ===')
console.log(`  分母 = languages.json 的 ${langs.length} 门真语言` +
  `（已剔除 WALS languages.csv 里的语系/语族占位行）`)
const buckets = [
  { lo: 0, hi: 30, label: '< 30' },
  { lo: 30, hi: 80, label: '30–79' },
  { lo: 80, hi: 150, label: '80–149' },
  { lo: 150, hi: Infinity, label: '≥ 150' },
]
const got = []
for (const b of buckets) {
  const rows = langs.filter((l) => {
    const c = featureCount[l.wals_id] ?? 0
    return c >= b.lo && c < b.hi
  })
  const wiki = rows.filter((l) => l.wiki_code).length
  const rate = rows.length ? wiki / rows.length : 0
  got.push({ label: b.label, n: rows.length, wiki, rate })
  console.log(`  ${b.label.padEnd(8)} ${String(rows.length).padStart(5)} 门, ` +
    `有维基 ${String(wiki).padStart(4)} 门 = ${(rate * 100).toFixed(1)}%`)
}
check('比例单调递增（记录越全越可能有维基版本）',
  got.every((g, i) => i === 0 || g.rate > got[i - 1].rate))
check('首尾差距悬殊（"双重缺席"成立）',
  got[got.length - 1].rate > got[0].rate * 10,
  `${(got[got.length - 1].rate * 100).toFixed(1)}% vs ${(got[0].rate * 100).toFixed(1)}%`)
// 修 kind 之前这里会算进 911 行语系占位行，导致首档虚高成 2575 门
check('首档不包含语系/语族占位行', got[0].n < 1700, `首档 ${got[0].n} 门`)

/* ---------------- 密度矩阵：阶梯形状 ---------------- */
console.log('\n=== 密度矩阵的阶梯形状 ===')
const BINS = 380
const cols = matrix.feature_ids.length
const featCount = matrix.values.map((row) => {
  let n = 0
  for (let i = 0; i < row.length; i++) if (row[i] != null) n++
  return n
})
const colOrder = featCount.map((_, i) => i).sort((a, b) => featCount[b] - featCount[a] || a - b)
const rowOrder = matrix.language_keys
  .map((_, i) => i)
  .sort((a, b) => (featureCount[matrix.language_keys[b]] ?? 0) - (featureCount[matrix.language_keys[a]] ?? 0))

const per = rowOrder.length / BINS
const grid = new Float32Array(cols * BINS)
for (let r = 0; r < BINS; r++) {
  const lo = Math.floor(r * per)
  const hi = Math.max(Math.floor((r + 1) * per), lo + 1)
  const n = hi - lo
  if (n <= 0) continue
  for (let c = 0; c < cols; c++) {
    const row = matrix.values[c]
    let hit = 0
    for (let k = lo; k < hi && k < rowOrder.length; k++) if (row[order(rowOrder, k)] != null) hit++
    grid[r * cols + c] = hit / n
  }
}
function order(arr, k) { return arr[k] }
function avgCell(r0, r1, c0, c1) {
  let s = 0
  let n = 0
  for (let r = r0; r < r1; r++) for (let c = c0; c < c1; c++) { s += grid[r * cols + c]; n++ }
  return n ? s / n : 0
}
const tl = avgCell(0, 20, 0, 20)
const tr = avgCell(0, 20, cols - 20, cols)
const bl = avgCell(BINS - 20, BINS, 0, 20)
const br = avgCell(BINS - 20, BINS, cols - 20, cols)
console.log(`  左上（记录最全的语言 × 覆盖最广的特征）= ${(tl * 100).toFixed(1)}%`)
console.log(`  右上（记录最全的语言 × 最冷门特征）  = ${(tr * 100).toFixed(1)}%`)
console.log(`  左下（记录最少的语言 × 覆盖最广特征）= ${(bl * 100).toFixed(1)}%`)
console.log(`  右下（记录最少的语言 × 最冷门特征）  = ${(br * 100).toFixed(1)}%`)
check('左上明显比右下密（阶梯可见）', tl > br * 3, `${(tl / Math.max(br, 1e-6)).toFixed(1)} 倍`)
check('沿横轴递减（左侧特征覆盖更广）', tl > tr)
check('沿纵轴递减（上方语言记录更全）', tl > bl)

/* ---------------- 整体稀疏度 ---------------- */
console.log('\n=== 稀疏度 ===')
let filled = 0
for (const row of matrix.values) for (const v of row) if (v != null) filled++
const total = cols * matrix.language_keys.length
console.log(`  ${matrix.language_keys.length} × ${cols} = ${total.toLocaleString('en-US')} 格，` +
  `有值 ${filled.toLocaleString('en-US')} (${(filled / total * 100).toFixed(1)}%)`)
check('稀疏度与探查一致（15.0%）', (filled / total * 100).toFixed(1) === '15.0')

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
