/**
 * 复现浏览器里的更新路径：先 setOption(A)，再用 **merge** setOption(B)，
 * 看第二次渲染有没有变化。之前的验证只做了"每次全新渲染"，漏掉了 merge 这条路径。
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

globalThis.echarts = echarts
;(0, eval)(readFileSync('web/public/vendor/world.js', 'utf8'))

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

function seriesFor(month) {
  const views = viewsAt(month)
  const maxViews = Math.max(...Object.values(views), 1)
  const contextData = hasCoords.map((l) => ({
    name: l.name, wals_id: l.wals_id, value: [l.longitude, l.latitude, 0],
  }))
  const vitalityData = vitalityLangs
    .filter((l) => views[l.wals_id] != null)
    .map((l) => ({
      name: l.name, wals_id: l.wals_id,
      value: [l.longitude, l.latitude, views[l.wals_id], 0],
    }))
  return [
    {
      id: 'ctx', type: 'scatter', coordinateSystem: 'geo',
      data: contextData, symbolSize: (v) => (v[2] ? 11 : 3.6),
    },
    {
      id: 'vit', type: 'scatter', coordinateSystem: 'geo',
      data: vitalityData,
      symbolSize: (v) => 5 + Math.sqrt(Number(v[2] ?? 0) / maxViews) * 34 + (v[3] ? 5 : 0),
    },
  ]
}

const OPT = { geo: { map: 'world', roam: true, zoom: 1.15, center: [10, 18] } }
const h = (s) => createHash('sha1').update(s).digest('hex').slice(0, 10)
const A = months[0], B = months[126]

console.log(`对比: ${A} → ${B}\n`)

// ---- 路径 1: merge（浏览器的真实路径）----
{
  const c = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: 520 })
  c.setOption({ ...OPT, series: seriesFor(A) })
  const s1 = c.renderToSVGString()
  c.setOption({ series: seriesFor(B) }) // <-- merge，和组件里一模一样
  const s2 = c.renderToSVGString()
  console.log('路径1  merge setOption({series})')
  console.log(`  A: ${s1.length.toLocaleString()} 字符  ${h(s1)}`)
  console.log(`  B: ${s2.length.toLocaleString()} 字符  ${h(s2)}`)
  console.log(`  有变化: ${s1 !== s2 ? '是' : '**否 —— 这就是 bug**'}`)
  c.dispose()
}

// ---- 路径 2: notMerge ----
{
  const c = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: 520 })
  c.setOption({ ...OPT, series: seriesFor(A) })
  const s1 = c.renderToSVGString()
  c.setOption({ ...OPT, series: seriesFor(B) }, true)
  const s2 = c.renderToSVGString()
  console.log('\n路径2  setOption(opt, true)  notMerge')
  console.log(`  有变化: ${s1 !== s2 ? '是' : '否'}`)
  c.dispose()
}

// ---- 路径 3: 只更新 data，symbolSize 用固定值（排除回调的因素）----
{
  const mk = (month) => seriesFor(month).map((s) => ({
    ...s,
    data: s.data.map((d) => ({ ...d, symbolSize: 5 + Math.sqrt(Number(d.value[2] ?? 0) / 1e6) * 34 })),
    symbolSize: undefined,
  }))
  const c = echarts.init(null, null, { renderer: 'svg', ssr: true, width: 900, height: 520 })
  c.setOption({ ...OPT, series: mk(A) })
  const s1 = c.renderToSVGString()
  c.setOption({ series: mk(B) })
  const s2 = c.renderToSVGString()
  console.log('\n路径3  merge + 逐项 symbolSize（不用回调）')
  console.log(`  有变化: ${s1 !== s2 ? '是' : '否'}`)
  c.dispose()
}
