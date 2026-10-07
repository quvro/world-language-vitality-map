/**
 * 真·渲染验证：用 ECharts 的 SSR 能力（无 DOM）在 Node 里实际渲染两个月，
 * 对比 SVG 输出，确认「拖时间轴 → 地图上的点确实变了」。
 *
 * 这一步很关键：之前只能验证代码能编译，无法验证行为。
 * SSR 渲染让"点的大小是否随时间轴改变"变成可测的事实。
 */
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import * as echartsNs from 'echarts'

const echarts = echartsNs.default ?? echartsNs
const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))

const langs = load('languages.json')
const ts = load('timeseries.json')
const byLang = ts.by_language
const months = Object.keys(byLang[Object.keys(byLang)[0]].views).sort()

// 注册世界地图：world.js 是传统脚本，用 globalThis.echarts 供它调用
globalThis.echarts = echarts
const worldSrc = readFileSync('web/public/vendor/world.js', 'utf8')
// eslint-disable-next-line no-eval
;(0, eval)(worldSrc)
console.log(`world map registered: ${!!echarts.getMap('world')}`)

const hasCoords = langs.filter((l) => l.latitude && l.longitude)
const vitalityLangs = langs
  .filter((l) => l.wiki_code && l.views_baseline != null && l.latitude && l.longitude)
  .sort((a, b) => (a.wals_id < b.wals_id ? -1 : 1))

function viewsAt(month) {
  const out = {}
  for (const [wid, s] of Object.entries(byLang)) {
    const v = s.views[month]
    if (v != null) out[wid] = v
  }
  return out
}

/** 与 WorldMap.vue 同构的 option */
function buildOption(month) {
  const views = viewsAt(month)
  const maxViews = Math.max(...Object.values(views), 1)

  const contextData = hasCoords.map((l) => ({
    name: l.name, wals_id: l.wals_id,
    value: [l.longitude, l.latitude, 0],
  }))

  const vitalityData = vitalityLangs
    .filter((l) => views[l.wals_id] != null)
    .map((l) => ({
      name: l.name, wals_id: l.wals_id,
      value: [l.longitude, l.latitude, views[l.wals_id], 0],
    }))

  return {
    geo: { map: 'world', roam: false, zoom: 1.15, center: [10, 18] },
    series: [
      {
        id: 'ctx', type: 'scatter', coordinateSystem: 'geo',
        data: contextData, symbolSize: (val) => (val[2] ? 11 : 3.6),
      },
      {
        id: 'vit', type: 'scatter', coordinateSystem: 'geo',
        data: vitalityData,
        symbolSize: (val) =>
          5 + Math.sqrt(Number(val[2] ?? 0) / maxViews) * 34 + (val[3] ? 5 : 0),
      },
    ],
  }
}

function renderSvg(month) {
  const chart = echarts.init(null, null, {
    renderer: 'svg', ssr: true, width: 900, height: 520,
  })
  chart.setOption(buildOption(month))
  const svg = chart.renderToSVGString()
  chart.dispose()
  return svg
}

/** 从 SVG 里抽出所有圆/符号的半径，用于证明大小真的变了 */
function radii(svg) {
  const out = []
  for (const m of svg.matchAll(/\br="([\d.]+)"/g)) out.push(parseFloat(m[1]))
  for (const m of svg.matchAll(/<path[^>]*d="M(-?[\d.]+)[ ,](-?[\d.]+)A/g)) {
    out.push(Math.abs(parseFloat(m[1])))
  }
  return out
}

const A = months[0]
const B = months[months.length - 1]
const mid = months[Math.floor(months.length / 2)]

console.log(`\n对比月份: ${A} → ${B}（中间参考 ${mid}）`)
const svgA = renderSvg(A)
const svgB = renderSvg(B)
const svgM = renderSvg(mid)

const h = (s) => createHash('sha1').update(s).digest('hex').slice(0, 12)
console.log(`\n  ${A}: SVG ${svgA.length.toLocaleString()} 字符  hash=${h(svgA)}`)
console.log(`  ${mid}: SVG ${svgM.length.toLocaleString()} 字符  hash=${h(svgM)}`)
console.log(`  ${B}: SVG ${svgB.length.toLocaleString()} 字符  hash=${h(svgB)}`)

const rA = radii(svgA), rB = radii(svgB)
const sumA = rA.reduce((a, b) => a + b, 0)
const sumB = rB.reduce((a, b) => a + b, 0)
console.log(`\n  符号数: ${A}=${rA.length}  ${B}=${rB.length}`)
console.log(`  半径总和: ${A}=${sumA.toFixed(0)}  ${B}=${sumB.toFixed(0)}`)
console.log(`  半径中位数: ${A}=${rA.sort((a,b)=>a-b)[Math.floor(rA.length/2)]}  ` +
  `${B}=${rB.sort((a,b)=>a-b)[Math.floor(rB.length/2)]}`)

// 逐月渲染一遍，看输出是否真的在变（而不是被缓存成同一帧）
const hashes = []
for (const m of [months[0], months[20], months[40], months[60], months[80], months[100], months[126]]) {
  hashes.push(h(renderSvg(m)))
}
console.log(`\n  7 个时间点渲染 hash: ${hashes.join(' ')}`)
const unique = new Set(hashes).size
console.log(`  不同 hash 数 = ${unique}/7`)

console.log('\n========================================')
if (unique === 7 && svgA !== svgB) {
  console.log('结论：时间轴确实改变地图渲染 —— 每个时间点输出都不同')
} else {
  console.log('结论：渲染未随时间变化，仍有问题')
  process.exitCode = 1
}
