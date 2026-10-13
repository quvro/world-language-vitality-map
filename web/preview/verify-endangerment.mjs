/**
 * 验证「活力之辨」视图的核心计算与结论。
 *
 * 这个视图是回答「活力到底是什么」的，所以它上面的每个数字都必须站得住：
 * 结论句「已灭绝的 51 种语言，一个有维基百科版本的都没有」如果算错，
 * 整个论点就垮了。
 */
import { readFileSync } from 'node:fs'
import { parseLocal } from '../shared/intent.js'

const D = 'data/processed/'
const load = (f) => JSON.parse(readFileSync(D + f, 'utf8'))
const langs = load('languages.json')
const E = load('endangerment.json')

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

/* ---- 复现 store.endangermentByWals ---- */
const ebw = {}
for (const l of langs) {
  const lv = E.by_glottocode[l.glottocode ?? ''] ?? E.by_iso639p3[(l.iso639p3 ?? '').toLowerCase()]
  if (lv) ebw[l.wals_id] = lv
}

const NAME = { 1: 'safe', 2: 'vulnerable', 3: 'definitely', 4: 'severely', 5: 'critically', 6: 'extinct' }

console.log('=== ① 存在性：濒危等级 × 是否有维基版本 ===')
const ex = []
for (const lv of [1, 2, 3, 4, 5, 6]) {
  const rows = langs.filter((l) => ebw[l.wals_id] === lv)
  const wiki = rows.filter((l) => l.wiki_code).length
  ex.push({ lv, n: rows.length, wiki, rate: rows.length ? wiki / rows.length : 0 })
  console.log(`  ${NAME[lv].padEnd(12)} ${String(rows.length).padStart(5)} 门, ` +
    `有维基 ${String(wiki).padStart(4)} = ${(ex[ex.length - 1].rate * 100).toFixed(1)}%`)
}
check('比例严格单调递减（濒危越重，越可能没有维基版本）',
  ex.every((d, i) => i === 0 || d.rate < ex[i - 1].rate))
check('safe 与 critically 差距 > 20 倍',
  ex[0].rate > ex[4].rate * 20,
  `${(ex[0].rate * 100).toFixed(1)}% vs ${(ex[4].rate * 100).toFixed(1)}%`)

/* ---- 结论句里的硬数字：已灭绝的语言一个都没有维基版本 ---- */
const extinct = ex.find((d) => d.lv === 6)
console.log()
console.log(`  已灭绝档：${extinct.n} 门，其中有维基版本 ${extinct.wiki} 门`)
check('结论句「已灭绝的一个都没有维基版本」成立', extinct.wiki === 0,
  `${extinct.wiki} 门`)

/* ---- ② 强度：样本量必须如实反映 ---- */
console.log('\n=== ② 强度：有维基版本者的阅读量中位数 ===')
const st = []
for (const lv of [1, 2, 3, 4, 5, 6]) {
  const v = langs
    .filter((l) => ebw[l.wals_id] === lv && l.wiki_code && l.views_recent != null)
    .map((l) => l.views_recent).sort((a, b) => a - b)
  if (!v.length) continue
  const med = v.length % 2 ? v[(v.length - 1) / 2] : (v[v.length / 2 - 1] + v[v.length / 2]) / 2
  st.push({ lv, n: v.length, med })
  console.log(`  ${NAME[lv].padEnd(12)} n=${String(v.length).padStart(3)}  中位=${Math.round(med).toLocaleString('en-US')}`)
}
const thin = st.filter((d) => d.n < 10)
console.log(`  样本 < 10 的档位 = ${thin.map((d) => `${NAME[d.lv]}(n=${d.n})`).join(', ') || '无'}`)
check('界面确实标注了「样本很小，谨慎解读」（存在样本 <10 的档位）', thin.length > 0,
  thin.length ? '有需要警示的档位' : '无小样本档位，警示文案可去掉')

/* ---- 口径说明里的数字 ---- */
console.log('\n=== 口径说明 ===')
const covered = langs.filter((l) => ebw[l.wals_id]).length
const unmatched = langs.length - covered
const unmatchedNoWiki = langs.filter((l) => !ebw[l.wals_id] && !l.wiki_code).length
console.log(`  已匹配 UNESCO = ${covered} / ${langs.length}`)
console.log(`  未匹配 = ${unmatched}，其中没有维基版本 = ${unmatchedNoWiki}`)
check('名录里 safe 占比极小（证明"未收录≠安全"这个警示是必要的）',
  E.counts['1'] / Object.values(E.counts).reduce((a, b) => a + b, 0) < 0.05,
  `safe 仅 ${E.counts['1']} 条`)
check('未匹配的语言里有相当一部分没有维基版本（说明未匹配 ≠ 安全）',
  unmatchedNoWiki / Math.max(unmatched, 1) > 0.5)

/* ---- 自然语言：濒危等级关键词 ---- */
console.log('\n=== 自然语言解析濒危等级 ===')
const CASES = [
  ['极度濒危的语言', [5]],
  ['濒危语言', [2, 3, 4, 5, 6]],
  ['安全的语言', [1]],
  ['已灭绝的语言', [6]],
  ['严重濒危的语言', [4]],
  ['critically endangered languages', [5]],
  ['extinct languages', [6]],
]
let nlFail = 0
for (const [q, want] of CASES) {
  const it = parseLocal(q, { families: [], features: [] })
  const got = it.endangermentLevels ?? []
  const ok = JSON.stringify(got) === JSON.stringify(want)
  if (!ok) nlFail++
  console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${q.padEnd(32)} -> ${JSON.stringify(got)}  期望 ${JSON.stringify(want)}`)
}
check('濒危关键词解析全部正确（含"濒危"这个公共子串的兜底）', nlFail === 0)
// 反向：不能误伤
const noEnd = parseLocal('非洲语区里语序是 SOV 的语言', { families: [], features: [] })
check('不相关的问法不会误判出濒危等级', noEnd.endangermentLevels === undefined,
  JSON.stringify(noEnd.endangermentLevels))

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
