/**
 * 「点没反应」的真正原因假设：不是没更新，而是**变化量小于 1 像素**。
 *
 * 当前大小公式: size = 5 + sqrt(v / max) * 34，其中 max 是当月全局最大浏览量。
 * 德语维基一个月有 ~7 亿浏览量，而绝大多数语言只有几千到几百万 ——
 * sqrt 压缩后，几乎所有语言都被挤在最小尺寸附近。
 *
 * 这里量化一下：拖时间轴时，典型语言的大小到底变了几像素？
 * 同时对比几种备选尺度，看哪种的变化是肉眼可见的。
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const ts = load('timeseries.json')
const byLang = ts.by_language

const vital = langs.filter((l) => l.wiki_code && l.views_baseline != null && l.latitude)
const months = Object.keys(byLang[Object.keys(byLang)[0]].views).sort()

function viewsAt(m) {
  const out = {}
  for (const l of vital) {
    const v = byLang[l.wals_id]?.views[m]
    if (v != null) out[l.wals_id] = v
  }
  return out
}

// 每门语言的十年峰值，供「相对自身」尺度使用
const ownMax = {}
for (const l of vital) {
  const s = byLang[l.wals_id]?.views ?? {}
  ownMax[l.wals_id] = Math.max(...Object.values(s), 1)
}

/** 当前实现：跨语言绝对比较 */
const scaleCurrent = (v, max) => 5 + Math.sqrt(v / max) * 34
/** 备选 A：相对该语言自己的十年峰值 */
const scaleRelative = (v, _max, wid) => 4 + Math.sqrt(v / ownMax[wid]) * 24
/** 备选 B：当月排名分位（越大越靠前） */
function makeRankScale(views) {
  const sorted = Object.entries(views).sort((a, b) => b[1] - a[1])
  const rank = new Map(sorted.map(([k], i) => [k, i]))
  const n = sorted.length
  return (v, _max, wid) => 4 + (1 - (rank.get(wid) ?? n) / n) * 26
}

function report(name, fn, samples) {
  const rows = samples.map((m) => {
    const views = viewsAt(m)
    const max = Math.max(...Object.values(views), 1)
    const sizes = new Map()
    for (const [wid, v] of Object.entries(views)) sizes.set(wid, fn(v, max, wid))
    return sizes
  })
  // 相邻采样点之间，每门语言大小变化的绝对值
  const deltas = []
  const spreads = []
  for (let i = 1; i < rows.length; i++) {
    for (const [wid, s] of rows[i]) {
      const prev = rows[i - 1].get(wid)
      if (prev != null) deltas.push(Math.abs(s - prev))
    }
  }
  for (const r of rows) {
    const arr = [...r.values()]
    spreads.push(Math.max(...arr) - Math.min(...arr))
  }
  deltas.sort((a, b) => a - b)
  const med = deltas[Math.floor(deltas.length / 2)]
  const p90 = deltas[Math.floor(deltas.length * 0.9)]
  const p99 = deltas[Math.floor(deltas.length * 0.99)]
  console.log(`\n  ${name}`)
  console.log(`    尺寸动态范围(各采样点) = ${spreads.map((s) => s.toFixed(0)).join(' / ')} px`)
  console.log(`    相邻时间点尺寸变化: 中位 ${med.toFixed(2)} px, ` +
    `p90 ${p90.toFixed(2)} px, p99 ${p99.toFixed(2)} px`)
  const visible = deltas.filter((d) => d >= 1.5).length / deltas.length
  console.log(`    变化 >= 1.5px（肉眼可辨）的比例 = ${(visible * 100).toFixed(1)}%`)
  return visible
}

const samples = [0, 20, 40, 60, 80, 100, 126].map((i) => months[i])
console.log(`采样月份: ${samples.join(', ')}`)
console.log(`有维基的语言数 = ${vital.length}`)

const a = report('当前实现: 5 + sqrt(v / 当月全局最大) * 34', scaleCurrent, samples)
const b = report('备选A: 相对该语言自身十年峰值', scaleRelative, samples)

// 排名尺度需要每个采样点单独构造
{
  const rows = samples.map((m) => {
    const views = viewsAt(m)
    const fn = makeRankScale(views)
    const sizes = new Map()
    for (const [wid, v] of Object.entries(views)) sizes.set(wid, fn(v, 0, wid))
    return sizes
  })
  const deltas = []
  for (let i = 1; i < rows.length; i++) {
    for (const [wid, s] of rows[i]) {
      const prev = rows[i - 1].get(wid)
      if (prev != null) deltas.push(Math.abs(s - prev))
    }
  }
  deltas.sort((x, y) => x - y)
  const med = deltas[Math.floor(deltas.length / 2)]
  const p90 = deltas[Math.floor(deltas.length * 0.9)]
  const visible = deltas.filter((d) => d >= 1.5).length / deltas.length
  console.log('\n  备选B: 当月排名分位')
  console.log(`    相邻时间点尺寸变化: 中位 ${med.toFixed(2)} px, p90 ${p90.toFixed(2)} px`)
  console.log(`    变化 >= 1.5px 的比例 = ${(visible * 100).toFixed(1)}%`)
}

console.log('\n========================================')
console.log(`结论：当前尺度的可见变化比例 = ${(a * 100).toFixed(1)}%，` +
  `备选A = ${(b * 100).toFixed(1)}%`)
