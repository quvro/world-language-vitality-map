/**
 * 用 SSR 渲染检查「选中高亮环」到底有没有画出来。
 *
 * 起因：我加了一个 halo 系列（transparent 填充 + 强调色描边），用户说看不见。
 * 读代码判断不了 ECharts 对 transparent 填充、data 级 symbolSize 的处理，
 * 所以直接渲染成 SVG 来看。
 *
 * 用直角坐标系而不是 geo：圆点的渲染路径与坐标系无关，
 * 而 world.js 是给浏览器用的 UMD，在 Node 里加载麻烦（且本机没有真实的
 * 地图视口概念）。要验的是「transparent 填充 + 描边 = 空心环」这一件事。
 */
import fs from 'node:fs'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
// 用 node_modules 里的 echarts 包（有真正的 CJS 导出）。
// public/vendor/echarts.min.js 是给浏览器用的 IIFE，require 它拿不到 API。
const echarts = require('echarts')
console.log('  echarts 版本 =', echarts.version)
console.log('  有 init/registerMap =', typeof echarts.init, typeof echarts.registerMap)

const ACCENT = '#e4572e'

function buildOption({ withHalo }) {
  const ctxData = [[0, 10], [1, 30], [2, 20]]
  const vitData = [
    { value: [0, 10, 5000000], symbolSize: 20,
      itemStyle: { color: '#4daf4a', borderColor: '#ffffff', borderWidth: 2, opacity: 1 } },
    { value: [1, 30, 200000], symbolSize: 12,
      itemStyle: { color: '#4daf4a', borderWidth: 1, opacity: 0.1 } },
  ]
  const haloData = withHalo
    ? [{ value: [0, 10, 5000000], symbolSize: 33 }]
    : []
  return {
    xAxis: { type: 'value', min: -1, max: 3 },
    yAxis: { type: 'value', min: 0, max: 40 },
    series: [
      { id: 'ctx', type: 'scatter', data: ctxData, z: 1,
        symbolSize: 11, itemStyle: { color: '#8dd3c7', opacity: 0.45 } },
      { id: 'vit', type: 'scatter', data: vitData, z: 2, symbolSize: 12 },
      {
        id: 'halo', type: 'effectScatter', data: haloData,
        z: 5, silent: true,
        showEffectOn: 'render',
        rippleEffect: { brushType: 'stroke', scale: 2.6, period: 3.2 },
        itemStyle: {
          color: 'transparent', borderColor: ACCENT, borderWidth: 3,
          shadowBlur: 8, shadowColor: ACCENT,
        },
      },
    ],
  }
}

function renderSvg(opts) {
  const chart = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 600, height: 400 })
  chart.setOption(buildOption(opts))
  const svg = chart.renderToSVGString()
  chart.dispose()
  return svg
}

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

const a = renderSvg({ withHalo: false })
const b = renderSvg({ withHalo: true })
const cnt = (s) => (s.match(new RegExp(ACCENT, 'gi')) || []).length

console.log('\n=== 不开 halo ===')
console.log(`  SVG ${a.length.toLocaleString()} B，强调色出现 ${cnt(a)} 次`)
console.log('=== 开 halo ===')
console.log(`  SVG ${b.length.toLocaleString()} B，强调色出现 ${cnt(b)} 次`)

check('halo 让 SVG 里多出强调色的绘制', cnt(b) > cnt(a), `${cnt(a)} → ${cnt(b)}`)

// 找出承载强调色的元素
const m = b.match(/<path[^>]*stroke="[^"]*e4572e[^"]*"[^>]*>/i)
  || b.match(/<circle[^>]*stroke="[^"]*e4572e[^"]*"[^>]*>/i)
  || b.match(/<[^>]*stroke="[^"]*e4572e[^"]*"[^>]*>/i)
if (m) {
  console.log('\n  承载强调色的元素:')
  console.log('    ' + m[0].slice(0, 300))
  const el = m[0]
  check('该元素有描边', /stroke="/.test(el))
  check('该元素不是实心填充（fill 为 none/transparent）',
    /fill="(none|transparent)"/i.test(el) || !/\bfill="/.test(el),
    (el.match(/\bfill="[^"]*"/) || ['(无 fill 属性)'])[0])
  // ECharts 的 SVG 符号画在单位圆里，靠 transform 缩放。
  // 所以 stroke-width 是**局部坐标**下的值，实际宽度 = stroke-width × 缩放系数。
  const tf = el.match(/matrix\(([\d.]+),/)
  const sw = el.match(/stroke-width="([\d.]+)"/)
  const scale = tf ? Number(tf[1]) : 1
  const eff = sw ? Number(sw[1]) * scale : 0
  check('描边实际宽度与设定一致（3px）', Math.abs(eff - 3) < 0.35,
    `局部 ${sw?.[1]} × 缩放 ${scale} = ${eff.toFixed(2)}px`)
  check('该元素是 effectScatter 画的（带系列序号元信息）',
    /ecmeta_series_index="2"/.test(el))
} else {
  check('能找到承载强调色的元素', false, '未找到 —— 这就是用户看不见的原因')
}

check('未选中时不该有强调色', cnt(a) === 0, `${cnt(a)} 次`)

const nPath = (s) => (s.match(/<path/g) || []).length
console.log(`\n  path 数: 不开 halo ${nPath(a)}，开 halo ${nPath(b)}`)
check('halo 至少多画了一个图形', nPath(b) > nPath(a))

fs.writeFileSync('web/preview/out-halo.svg', b)
console.log('  已存 web/preview/out-halo.svg 供人工查看')

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
