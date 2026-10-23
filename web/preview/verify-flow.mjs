/**
 * 验证流向图（桑基）的数据结构。
 *
 * 桑基图最容易出的错是**流带总数对不上**：中间列的节点值必须等于进出的流带之和，
 * 否则 ECharts 会把节点画得忽大忽小，而且看起来"好像没问题"。所以这里从
 * 真实 store 独立重算一遍三列结构，验四条守恒。
 */
import { createHarness } from './_harness.mjs'

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

const h = await createHarness()
try {
  const s = await h.freshStore()
  const TOP_N = 14
  const ebw = s.endangermentByWals
  const famAll = s.familyList
  const keep = new Set(famAll.slice(0, TOP_N).map((f) => f.family))

  console.log(`  语系总数 ${famAll.length}，取前 ${TOP_N} 个`)
  const covered = famAll.slice(0, TOP_N).reduce((a, f) => a + f.count, 0)
  console.log(`  前 ${TOP_N} 个语系覆盖 ${covered} / ${s.langs.length} 门 `
    + `(${(covered / s.langs.length * 100).toFixed(1)}%)`)

  /* ---------- 1. 三列结构 ---------- */
  const trip = new Map()
  const famCount = new Map()
  let othersLangs = 0
  const othersFams = new Set()
  const levels = new Set()
  let noAes = 0
  for (const l of s.langs) {
    const raw = l.family || ''
    const f = keep.has(raw) ? raw : '__other'
    if (f === '__other') { othersLangs += 1; if (raw) othersFams.add(raw) }
    famCount.set(f, (famCount.get(f) ?? 0) + 1)
    const lv = ebw[l.wals_id]
    if (!lv) { noAes += 1; continue }
    levels.add(lv)
    const k = `${f}|${lv}|${l.wiki_code ? 1 : 0}`
    trip.set(k, (trip.get(k) ?? 0) + 1)
  }

  console.log('\n=== 1. 守恒：三列总数必须相等 ===')
  let sumTriple = 0
  const outFam = new Map()
  const outLv = new Map()
  const inW = new Map()
  for (const [k, n] of trip) {
    const [f, lv, has] = k.split('|')
    sumTriple += n
    outFam.set(f, (outFam.get(f) ?? 0) + n)
    outLv.set(lv, (outLv.get(lv) ?? 0) + n)
    inW.set(has, (inW.get(has) ?? 0) + n)
  }
  const withAes = s.langs.filter((l) => ebw[l.wals_id]).length
  check('三元组之和 = 有濒危等级的语言数', sumTriple === withAes, `${sumTriple} vs ${withAes}`)
  check('第一列出边之和守恒',
    [...outFam.values()].reduce((a, b) => a + b, 0) === sumTriple)
  check('第二列进出守恒',
    [...outLv.values()].reduce((a, b) => a + b, 0) === sumTriple)
  check('第三列入边之和守恒',
    [...inW.values()].reduce((a, b) => a + b, 0) === sumTriple)

  /* ---------- 2. 语系总量要能对上 ---------- */
  console.log('\n=== 2. 语系分桶 ===')
  check('各语系计数之和 = 全部语言数',
    [...famCount.values()].reduce((a, b) => a + b, 0) === s.langs.length,
    `${[...famCount.values()].reduce((a, b) => a + b, 0)} vs ${s.langs.length}`)
  // 原来这里断言「其他语系不应压过最大语系」—— 这条**是错的**。
  // 语系长尾是真的：254 个语系里前 14 个只覆盖 63.7%，剩下 240 个小语系
  // 合起来有 965 门语言，必然比最大的尼日尔-刚果(324)多。
  // 消不掉，所以改成两条真正能保护观众的约束：
  //   ① 它排在最后（上面已验）② 它不能藏掉太多，否则这视图等于在讲"其他"
  check('长尾占比 < 50%（否则这个视图主要在讲"其他语系"）',
    othersLangs / s.langs.length < 0.5,
    `${(othersLangs / s.langs.length * 100).toFixed(1)}%`)
  console.log(`    其他语系合并 ${othersFams.size} 个语系 / ${othersLangs} 门语言`)
  // 语系长尾很长（254 个，前 14 个只覆盖 63.7%），所以「其他」必然是个大桶。
  // 既然消不掉，就要求它：① 排在最底部 ② 标签里写明构成。
  // 组件里的 node 顺序必须是「真实语系按大小降序，__other 最后」。
  const src = await import('node:fs').then((m) => m.readFileSync(
    'web/src/components/FlowView.vue', 'utf8'))
  check('语系按大小排序，__other 追加到末尾（否则最宽的一条是没有意义的灰块）',
    /\.sort\(\(a, b\) => b\[1\] - a\[1\]\)[\s\S]{0,160}famOrder\.push\('__other'\)/.test(src))
  check('「其他」的标签写明合并了多少个小型语系',
    /othersSmall\(othersFams\.size/.test(src))
  console.log(`    长尾占比：其他语系 ${(othersLangs / s.langs.length * 100).toFixed(1)}% —— 页脚已注明`)

  /* ---------- 3. 图要讲的那句话是否成立 ---------- */
  console.log('\n=== 3. 结论是否成立：右侧宽的那支必须是"没有维基" ===')
  const w0 = inW.get('0') ?? 0
  const w1 = inW.get('1') ?? 0
  check('没有维基版本的那支更宽', w0 > w1, `无 ${w0} vs 有 ${w1}（${(w0 / sumTriple * 100).toFixed(1)}% 无）`)
  // 逐语系检查：每个语系是否也大体如此（否则"每个语系都一样"那句就是假话）
  const perFam = [...outFam.keys()].map((f) => {
    let nowiki = 0
    let tot = 0
    for (const [k, n] of trip) {
      if (!k.startsWith(`${f}|`)) continue
      tot += n
      if (k.endsWith('|0')) nowiki += n
    }
    return { f, share: tot ? nowiki / tot : 0, tot }
  }).filter((x) => x.tot >= 20)
  const allLean = perFam.every((x) => x.share > 0.5)
  check('每个语系（>=20 门语言）里"无维基"都占多数',
    allLean,
    allLean ? `${perFam.length} 个语系全部如此`
      : `例外：${perFam.filter((x) => x.share <= 0.5).map((x) => `${x.f}=${(x.share * 100).toFixed(0)}%`).join(', ')}`)

  /* ---------- 4. 极端：没有濒危等级的语言不能被悄悄丢掉 ---------- */
  console.log('\n=== 4. 没有濒危等级的语言 ===')
  console.log(`    ${noAes} 门（图里不进第二列，页脚已注明）`)
  check('缺失量不该超过 5%', noAes / s.langs.length < 0.05,
    `${(noAes / s.langs.length * 100).toFixed(1)}%`)
} finally {
  h.cleanup()
}

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
