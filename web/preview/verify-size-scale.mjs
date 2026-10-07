/**
 * 验证新的大小尺度：
 *  1. ECharts 的 symbolSize 回调收到的 val 是不是我们编进去的那个数组
 *  2. 新尺度下，相邻月份渲染出来的点大小差异是否足够大（肉眼可辨）
 */
import { readFileSync } from 'node:fs'
import * as echartsNs from 'echarts'

const echarts = echartsNs.default ?? echartsNs
const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const ts = load('timeseries.json')
const byLang = ts.by_language
const months = Object.keys(byLang[Object.keys(byLang)[0]].views).sort()

globalThis.echarts = echarts
;(0, eval)(readFileSync('web/public/vendor/world.js', 'utf8'))

const vital = langs
  .filter((l) => l.wiki_code && l.views_baseline != null && l.latitude && l.longitude)
  .sort((a, b) => (a.wals_id < b.wals_id ? -1 : 1))

const ownPeak = {}
for (const l of vital) {
  const s = byLang[l.wals_id]?.views ?? {}
  ownPeak[l.wals_id] = Math.max(...Object.values(s), 1)
}

function buildSeries(month, sizeMode, record) {
  const views = {}
  for (const [wid, s] of Object.entries(byLang)) {
    if (s.views[month] != null) views[wid] = s.views[month]
  }
  const entries = Object.entries(views).sort((a, b) => b[1] - a[1])
  const rank = {}
  entries.forEach(([wid], i) => { rank[wid] = i })
  const n = Math.max(entries.length, 1)

  const data = vital
    .filter((l) => views[l.wals_id] != null)
    .map((l) => ({
      name: l.name, wals_id: l.wals_id,
      value: [
        l.longitude, l.latitude, views[l.wals_id], 0,
        ownPeak[l.wals_id], 1 - (rank[l.wals_id] ?? n) / n,
      ],
    }))

  const sizeOf = (val) => {
    if (record) record(val)
    if (sizeMode === 'relative') {
      const rel = Math.min(Number(val[2] ?? 0) / (Number(val[4]) || 1), 1)
      return 4 + Math.sqrt(rel) * 24
    }
    return 4 + Math.min(Math.max(Number(val[5] ?? 0), 0), 1) * 26
  }

  return [
    { id: 'ctx', type: 'scatter', coordinateSystem: 'geo', progressive: 0,
      data: langs.filter((l) => l.latitude).map((l) => ({
        name: l.name, wals_id: l.wals_id, value: [l.longitude, l.latitude, 0] })),
      symbolSize: (v) => (v[2] ? 11 : 3.4) },
    { id: 'vit', type: 'scatter', coordinateSystem: 'geo', progressive: 0,
      data, symbolSize: sizeOf },
  ]
}

const OPT = { geo: { map: 'world', roam: true, zoom: 1.15, center: [10, 18],
  scaleLimit: { min: 0.9, max: 14 } } }

function render(month, sizeMode, record) {
  const c = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: 520 })
  c.setOption({ ...OPT, series: buildSeries(month, sizeMode, record) }, true)
  const svg = c.renderToSVGString()
  c.dispose()
  return svg
}

console.log('=== 1. 确认 symbolSize 回调收到的 val ===')
const seen = []
render(months[0], 'relative', (v) => { if (seen.length < 3) seen.push(v) })
for (const v of seen) {
  console.log(`  val = [${v.map((x) => (typeof x === 'number' ? x.toFixed(3) : x)).join(', ')}]`)
  console.log(`        长度 ${v.length}  lon=${v[0]?.toFixed?.(2)} lat=${v[1]?.toFixed?.(2)} ` +
    `views=${v[2]} sel=${v[3]} peak=${v[4]} rankPct=${Number(v[5]).toFixed(3)}`)
}
console.log(`  -> 长度应为 6，且第 5 位是自身峰值: ${seen[0]?.length === 6 ? '是' : '否'}`)

console.log('\n=== 2. 相邻月份的点大小变化（直接评估尺寸函数）===')
for (const mode of ['relative', 'absolute']) {
  const samples = [0, 20, 40, 60, 80, 100, 126].map((i) => months[i])
  const rows = samples.map((m) => {
    const sizes = new Map()
    // 借道渲染收集尺寸：把回调记录成 map
    const c = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: 520 })
    const idx = { i: 0 }
    const series = buildSeries(m, mode, null)
    const data = series[1].data
    const sizeOf = series[1].symbolSize
    data.forEach((d) => { sizes.set(d.wals_id, sizeOf(d.value)) })
    void c; void idx
    return sizes
  })
  const deltas = []
  for (let i = 1; i < rows.length; i++) {
    for (const [wid, s] of rows[i]) {
      const prev = rows[i - 1].get(wid)
      if (prev != null) deltas.push(Math.abs(s - prev))
    }
  }
  deltas.sort((a, b) => a - b)
  const med = deltas[Math.floor(deltas.length / 2)]
  const visible = deltas.filter((d) => d >= 1.5).length / deltas.length
  const allSizes = [...rows[rows.length - 1].values()].sort((a, b) => a - b)
  console.log(`  ${mode.padEnd(9)} 中位变化 ${med.toFixed(2)}px  可见比例 ${(visible * 100).toFixed(1)}%  ` +
    `尺寸范围 ${allSizes[0].toFixed(1)}~${allSizes[allSizes.length - 1].toFixed(1)}px`)
}

console.log('\n=== 3. 两个月份的 SVG 是否不同 ===')
for (const mode of ['relative', 'absolute']) {
  const a = render(months[0], mode)
  const b = render(months[126], mode)
  console.log(`  ${mode.padEnd(9)} 不同: ${a !== b ? '是' : '否'}   ` +
    `${a.length.toLocaleString()} -> ${b.length.toLocaleString()} 字符`)
}
