/**
 * 回归防线：WorldMap 里读到的每个 store 字段，必须能触发重绘。
 *
 * 起因是一个真实的 bug：给「只看选中」加了 store.hideUnselected，
 * 也把它写进了 computed 的过滤逻辑，**却忘了加 watcher**。
 * ECharts 是命令式渲染 —— 状态变了没人调 render()，那个开关点了完全没反应。
 *
 * 规则：每个被读到的 store 字段，要么出现在「被监听的 computed 及其调用到的
 * 辅助函数」体内，要么出现在某条显式 watch 的源码里。
 *
 * 注意辅助函数也算覆盖范围：数据 computed 会调用 keepLang / baseColor / sizeOf，
 * 这些函数体在被监听范围之外，但它们读取的字段同样会触发 computed 重算。
 */
import { readFileSync } from 'node:fs'

const FILE = 'web/src/components/WorldMap.vue'
const src = readFileSync(FILE, 'utf8')
const SCRIPT_START = src.indexOf('<script')
const script = src.slice(SCRIPT_START, src.indexOf('</script>'))

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

/** 用括号配对取出从 name 声明处开始的源码范围（绝对位置） */
function rangeOf(name) {
  const re = new RegExp(
    `(?:const\\s+${name}\\s*=\\s*(?:computed\\(|ref\\()|function\\s+${name}\\s*\\()`, 'g')
  const m = re.exec(src)
  if (!m) return null
  // 从声明处往后找第一个 '{' 再配对；没有 '{' 就取到行尾
  const brace = src.indexOf('{', m.index)
  const lineEnd = src.indexOf('\n', m.index)
  if (brace < 0 || (lineEnd >= 0 && lineEnd < brace)) {
    return { from: m.index, to: lineEnd < 0 ? src.length : lineEnd }
  }
  let depth = 0
  for (let j = brace; j < src.length; j++) {
    if (src[j] === '{') depth++
    else if (src[j] === '}') {
      depth--
      if (depth === 0) return { from: m.index, to: j + 1 }
    }
  }
  return null
}

/* ---- 覆盖范围 ---- */
const WATCHED = ['contextData', 'vitalityData', 'haloData']
// 数据 computed 会调用到的辅助函数：它们读的字段同样会触发重算
const HELPERS = ['keepLang', 'baseColor', 'trendColor', 'sizeOf']
// 渲染路径：buildSeries 决定 series 内容，OPT_BASE 里的 geo.nameMap 依赖 lang
const RENDER = ['buildSeries', 'render', 'OPT_BASE']

const ranges = []
for (const n of [...WATCHED, ...HELPERS, ...RENDER]) {
  const r = rangeOf(n)
  if (r) ranges.push({ name: n, ...r })
  else console.log(`  (未找到 ${n}，跳过)`)
}

/* ---- 显式 watch 的源码文本 ---- */
const watchText = []
for (const m of script.matchAll(/watch\(/g)) {
  watchText.push(script.slice(m.index, m.index + 260))
}
const watchBlob = watchText.join('\n')

console.log('=== 覆盖面 ===')
console.log('  被监听的 computed :', WATCHED.join(', '))
console.log('  计入的辅助函数    :', HELPERS.join(', '))
console.log('  渲染路径          :', RENDER.join(', '))
console.log('  显式 watch 条数   :', watchText.length)

/* ---- 逐字段检查 ---- */
const SKIP = new Set(['select', 'toggleComparison', 'clearFilters', 'load'])
/**
 * 有理由的例外：不影响已生成的 option，因此不需要触发 ECharts 重绘。
 * 每一条都要写清理由，避免这个检查被"顺手放行"变成摆设。
 */
const NO_REPAINT_NEEDED = {
  currentMonth:
    '只经 monthLabel 用在 tooltip 的 formatter（悬停时才求值）与 Vue 模板里' +
    '（Vue 自己响应式更新），都没有被烘进 option',
}
const reads = new Map()
for (const m of script.matchAll(/store\.([A-Za-z_$][\w$]*)/g)) {
  const field = m[1]
  if (SKIP.has(field)) continue
  const abs = SCRIPT_START + m.index
  if (!reads.has(field)) reads.set(field, [])
  reads.get(field).push(abs)
}

console.log('\n=== 逐字段检查 ===')
const uncovered = []
let coveredInComputed = 0
let coveredInWatch = 0
let exempted = 0
for (const [field, positions] of [...reads.entries()].sort()) {
  const inRange = positions.some((p) => ranges.some((r) => p >= r.from && p <= r.to))
  const inWatch = new RegExp(`store\\.${field}\\b`).test(watchBlob)
  const exempt = NO_REPAINT_NEEDED[field]
  const ok = inRange || inWatch || !!exempt
  if (inRange) coveredInComputed++
  else if (inWatch) coveredInWatch++
  else if (exempt) exempted++
  else uncovered.push(field)
  console.log(`  ${ok ? 'OK  ' : 'FAIL'} store.${field.padEnd(18)} ` +
    `${inRange ? '[被监听的 computed / 辅助函数]' : ''}` +
    `${inWatch ? '[显式 watch]' : ''}` +
    `${exempt ? '[有理由的例外]' : ''}`)
}
console.log(`\n  经 computed 覆盖 ${coveredInComputed} 个，经显式 watch 覆盖 ${coveredInWatch} 个，` +
  `有理由的例外 ${exempted} 个`)
for (const [k, v] of Object.entries(NO_REPAINT_NEEDED)) console.log(`    例外 ${k}: ${v}`)
check('所有被读到的 store 字段都能触发重绘', uncovered.length === 0,
  uncovered.join(', '))

/* ---- 结构不变量 ---- */
console.log('\n=== 结构不变量 ===')
check('series 的 id 稳定（merge 渲染依赖它）',
  ["id: 'ctx'", "id: 'vit'", "id: 'halo'"].every((s) => src.includes(s)))
check('halo 是 silent（不吃鼠标事件，否则挡住底下点的 tooltip）',
  /id: 'halo'[\s\S]{0,220}silent: true/.test(src))
check('halo 在活力层找不到时退回底图（否则选到无维基语言就没有环）',
  /inVit\s*\?\?\s*contextData\.value\.find/.test(src))
check('远景聚合模式下 halo 退回到"包含选中语言的聚合块"',
  /x\.value\[2\] === 1/.test(src))
check('聚合块按数量放大（块越大语言越多）',
  /val\.length > 4[\s\S]{0,140}Math\.sqrt\(val\[4\]\)/.test(src))
// —— 下面这几条都是「点跟地图错位」的根因，实测踩过 ——
check('底图系列关掉了更新动画（否则切换密度/逐点时新点会从旧坐标飞过去，看着像错位）',
  /id: 'ctx'[\s\S]{0,400}animation: false/.test(src))
// 最强的一条保证：根本不在 georoam 里做任何事，
// 于是缩放期间一次 setOption 都不发生，不可能打断 geo 的缩放补间。
check('不监听 georoam（缩放期间不发生任何 setOption，从根上避免地图错位）',
  !/on\('georoam'/.test(src))
check('密度/逐点由显式开关控制，不跟随缩放自动切换',
  /store\.mapDensity/.test(src) && !/AGG_ZOOM/.test(src))
check('聚合块位置用格内质心，不是第一个语言的坐标（否则块偏向格子一角，看着像错位）',
  /lngSum \/ c\.n[\s\S]{0,40}c\.latSum \/ c\.n/.test(src))
check('「只看选中」的过滤同时作用于两个图层',
  (src.match(/keepLang\(l\.wals_id\)/g) || []).length >= 2)
check('选中点用的是白色内圈 + 外层强调色光环（靶心），不是单纯加粗描边',
  /borderColor: isSel[\s\S]{0,40}C\.surface/.test(src) &&
  /borderWidth: isSel \? 2\.5/.test(src))
check('「高亮」作用于**筛选命中的全部语言**，不只是选中的那一个',
  /opacity: isSel \? 1 : hit \? \(filtering \? 1 : 0\.5\) : 0\.05/.test(src) &&
  /filtering && hit \? 1 : 0\]/.test(src))
check('未命中的点压到近乎隐形但保留（地理参照）',
  /opacity: !hit \? 0\.05 :/.test(src))
// 这一条来自一个真实的坑：effectScatter 的涟漪颜色默认取 itemStyle.color，
// 而 halo 的 itemStyle.color 是 transparent（为了只显示描边），
// 于是涟漪也跟着透明 —— 表现是"能看见静止的红圈，但它不扩散"。
check('涟漪显式指定了颜色（否则会跟着 transparent 的填充一起隐形）',
  /rippleEffect: \{[^}]*color: C\.accent/.test(src))
check('不再有逐字段枚举的 watcher（那个写法漏过一次）',
  !/watch\(\(\) => store\.colorBy/.test(src))

// —— 语系星群（选中语言时在地图上直接画从属关系）——
check('语系连线与轮廓两层都在，且都是 silent（不吃鼠标事件）',
  /id: 'famstar'[\s\S]{0,200}silent: true/.test(src)
  && /id: 'famhull'[\s\S]{0,200}silent: true/.test(src))
check('三层（连线 / 轮廓 / 浅强调底圈）都在重绘监听里',
  /watch\(\[contextData, vitalityData, haloData, famStar, famHull, famGlow\]/.test(src))
check('跨 180° 经线的语系跳过轮廓（否则会画出一个横跨地图的假多边形）',
  /spansDateline\(pts\)\) return \[\]/.test(src))
check('跳过轮廓时在说明里写出来（否则用户以为轮廓坏了）',
  /selFamily\.dateline/.test(src) && /famDateline/.test(src))
check('轮廓排在底图之下（z < 1），不会盖住语言点',
  /id: 'famhull'[\s\S]{0,160}z: 0\.\d/.test(src))
// 用户要求「线链接的点也有一个比较浅的强调色」。
// 做成独立底圈层而不是改点本身填充：填充色承载编码（语区/趋势），改了会丢信息。
check('连线那头的点有浅强调色底圈，且不覆盖点的填充色',
  /id: 'famglow'[\s\S]{0,300}withAlpha\(C\.accent, 0\.16\)/.test(src))
check('底圈的 z 在底图(1)与活力层(2)之间，从点背后露出',
  /id: 'famglow'[\s\S]{0,160}z: 1\.5/.test(src))
check('同语系的点在逐点模式下描边也用强调色（与底圈呼应）',
  /inFam\s*\?\s*withAlpha\(C\.accent/.test(src))
check('活力层对同语系的点也换强调色描边',
  /fatallyAbsent/.test(src) || /!isSel && famIds\.value\?\.has\(l\.wals_id\)[\s\S]{0,60}withAlpha\(C\.accent, 0\.85\)/.test(src))
check('强调色用的是半透明 rgba，不是硬色（才叫"浅"）',
  /function withAlpha/.test(src) && /rgba\(\$\{r\},\$\{g\},\$\{b\},\$\{a\}\)/.test(src))

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
