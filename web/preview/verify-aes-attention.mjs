/**
 * 验证「濒危 × 关注」视图的三个结论。
 *
 * 这些是要拿去讲的结论，每个数字都必须站得住：
 *   1. 存在性随濒危程度急剧下降
 *   2. 最大的一群是「未濒危却在数字世界缺席」的语言
 *   3. 少数已灭绝的语言在数字空间反而在增长
 * 另外验证那个**表现陷阱**：散点图只覆盖有维基版本的语言，
 * 必须确认视图确实把"缺席"也显示出来了，否则会误导。
 */
import { readFileSync } from 'node:fs'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const A = load('aes.json')
const U = load('endangerment.json')

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

/* ---- 复现 store.endangermentByWals（AES 优先，UNESCO 补缺）---- */
const ebw = {}
const srcCount = { aes: 0, unesco: 0, none: 0 }
for (const l of langs) {
  const gc = l.glottocode ?? ''
  const iso = (l.iso639p3 ?? '').toLowerCase()
  let lv = A.by_glottocode[gc]
  if (lv) srcCount.aes++
  else {
    lv = U.by_glottocode[gc] ?? U.by_iso639p3[iso]
    if (lv) srcCount.unesco++
    else srcCount.none++
  }
  if (lv) ebw[l.wals_id] = lv
}

const NAME = { 1: '未濒危', 2: '受威胁', 3: '转移中', 4: '垂危', 5: '几近灭绝', 6: '已灭绝' }

console.log('=== 覆盖与来源 ===')
const cov = Object.keys(ebw).length
console.log(`  AES ${srcCount.aes} + UNESCO 补 ${srcCount.unesco} = ${cov} / ${langs.length}` +
  ` (${(cov / langs.length * 100).toFixed(1)}%)，未覆盖 ${srcCount.none}`)
check('合并量表覆盖率 > 95%', cov / langs.length > 0.95)
check('AES 是主力来源（占已覆盖的 > 90%）', srcCount.aes / cov > 0.9,
  `${(srcCount.aes / cov * 100).toFixed(1)}%`)

/* ---- 结论 1 ---- */
console.log('\n=== 结论 1：存在性随濒危程度下降 ===')
const ex = []
for (const lv of [1, 2, 3, 4, 5, 6]) {
  const rows = langs.filter((l) => ebw[l.wals_id] === lv)
  const wiki = rows.filter((l) => l.wiki_code).length
  ex.push({ lv, n: rows.length, wiki, rate: rows.length ? wiki / rows.length : 0 })
  console.log(`  ${NAME[lv].padEnd(6)} ${String(rows.length).padStart(5)} 门  ` +
    `有维基 ${String(wiki).padStart(4)} = ${(ex[ex.length - 1].rate * 100).toFixed(1)}%`)
}
check('首档与末档差距 > 10 倍', ex[0].rate > ex[5].rate * 10,
  `${(ex[0].rate * 100).toFixed(1)}% vs ${(ex[5].rate * 100).toFixed(1)}%`)
check('整体趋势向下（末档低于首档）', ex[5].rate < ex[0].rate)

/* ---- 结论 2：最大的缺席群体是"未濒危" ---- */
console.log('\n=== 结论 2：最大的缺席群体是「未濒危」 ===')
const noWiki = langs.filter((l) => ebw[l.wals_id] && !l.wiki_code)
const byLevel = {}
for (const l of noWiki) byLevel[ebw[l.wals_id]] = (byLevel[ebw[l.wals_id]] ?? 0) + 1
console.log(`  已定级但无维基版本的语言 = ${noWiki.length}`)
for (const lv of [1, 2, 3, 4, 5, 6]) {
  console.log(`    ${NAME[lv].padEnd(6)} ${String(byLevel[lv] ?? 0).padStart(5)}`)
}
const notEnd = byLevel[1] ?? 0
const endangeredMissing = [2, 3, 4, 5, 6].reduce((a, k) => a + (byLevel[k] ?? 0), 0)
// 注意措辞：793 是**单一等级里最多**的，但五个濒危档合计更多（1557）。
// 早先我把结论写成"最大的一群"，被这条检查抓住了 —— 所以这里明确区分两件事。
const maxLevel = Math.max(...[1, 2, 3, 4, 5, 6].map((k) => byLevel[k] ?? 0))
check('「未濒危」是缺席数量最多的**单一等级**', notEnd === maxLevel,
  `${notEnd} 是最大单一档`)
check('但五个濒危档合计缺席更多（结论不能写成"最大的一群"）',
  endangeredMissing > notEnd, `${endangeredMissing} vs ${notEnd}`)

/* ---- 结论 3：已灭绝却在增长 ---- */
console.log('\n=== 结论 3：已灭绝/几近灭绝却仍有维基版本 ===')
const revive = langs.filter((l) => ebw[l.wals_id] >= 5 && l.wiki_code)
      .sort((a, b) => (b.views_recent ?? 0) - (a.views_recent ?? 0))
for (const l of revive) {
  const g = l.growth != null ? `${l.growth >= 0 ? '+' : ''}${(l.growth * 100).toFixed(0)}%` : '—'
  console.log(`  ${NAME[ebw[l.wals_id]]}  ${l.name.padEnd(22)} ` +
    `阅读/月=${(l.views_recent ?? 0).toLocaleString('en-US').padStart(11)}  十年=${g}`)
}
check('确实存在「已灭绝但有维基版本」的语言', revive.length > 0, `${revive.length} 门`)
check('其中至少一门十年在增长',
  revive.some((l) => l.growth != null && l.growth > 0))
const cornish = revive.find((l) => l.wiki_code === 'kw')
check('康沃尔语在列表里（口语已灭绝但维基在增长）', !!cornish,
  cornish ? `十年 ${(cornish.growth * 100).toFixed(0)}%` : '未找到')

/* ---- 表现陷阱：散点图覆盖不到大多数语言 ---- */
console.log('\n=== 表现陷阱检查 ===')
const plot = langs.filter((l) => l.wiki_code && (l.views_recent ?? 0) > 0 && ebw[l.wals_id])
console.log(`  散点图能画出的点 = ${plot.length}`)
console.log(`  已定级但画不出来的 = ${cov - plot.length}`)
check('散点图覆盖的不足已定级语言的一半（所以必须另配"缺席"条）',
  plot.length < cov * 0.5,
  `${plot.length} / ${cov} = ${(plot.length / cov * 100).toFixed(1)}%`)
check('视图里确实有"缺席"面板（源码检查）',
  readFileSync('web/src/components/EndangermentView.vue', 'utf8').includes('absence'))

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
