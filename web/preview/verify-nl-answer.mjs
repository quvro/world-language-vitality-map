/**
 * 验证「检索 + 回答」这一段。
 *
 * 重点不是文案好不好看，而是三个**不变量**：
 *   1. 证据里的数字必须与 store.filtered 完全一致（不能另算一套）
 *   2. 答案里出现的数字必须来自证据（不能有来源不明的数）
 *   3. 没有命中 / 有命中 两种情况下都不崩，且各自给出合适的结论
 */
import { createHarness } from './_harness.mjs'

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

const h = await createHarness()
try {
  const { buildEvidence, composeAnswer, intentText } = await h.load('answer.js')
  const { parseLocal } = await h.load('intent.js')
  const s = await h.freshStore()

  const label = (r) => r.name
  const ctx = { families: s.familyList.map((f) => f.family), features: [] }

  const pack = (rows) => buildEvidence({
    rows,
    total: s.langs.length,
    ebw: s.endangermentByWals,
    featCount: s.featureCount,
    label,
  })

  /* ---------- 1. 有命中的情况 ---------- */
  console.log('=== 1. 「极度濒危」这类问题 ===')
  const q1 = '极度濒危的语言'
  const i1 = parseLocal(q1, ctx)
  s.applyIntent(i1)
  const e1 = pack(s.filtered)
  const a1 = composeAnswer({ question: q1, intent: i1, evidence: e1, lang: 'zh' })
  check('证据里的 count 与 store.filtered 一致',
    e1.count === s.filtered.length, `${e1.count} vs ${s.filtered.length}`)
  check('有命中', e1.count > 0, `${e1.count} 门`)
  check('答案有标题 / 结论 / 要点',
    !!a1.title && !!a1.lead && a1.bullets.length > 0,
    `${a1.bullets.length} 条要点`)
  console.log(`    标题：${a1.title}`)
  console.log(`    结论：${a1.lead.slice(0, 60)}…`)
  for (const b of a1.bullets.slice(0, 3)) console.log(`    · ${b.replace(/\*\*/g, '')}`)
  check('濒危等级分布之和 = 命中数（有等级的才计入，允许小于）',
    e1.levels.reduce((x, y) => x + y.n, 0) <= e1.count)
  check('意图能写成一句话', intentText(i1, true).length > 0, intentText(i1, true))

  /* ---------- 2. 答案里的数字必须来自证据 ---------- */
  console.log('\n=== 2. 答案里的数字是否都来自证据 ===')
  // 百分比是从证据里的比率派生出来的（例如 51.13 → "51.1%"），
  // 单独放行；这里只追溯**计数类**数字是否都能在证据里找到。
  const rawText = (a1.bullets.join(' ') + a1.lead + a1.caveats.join(' '))
  const nums = rawText.replace(/[-+]?\d+(\.\d+)?%/g, ' ').match(/\d[\d,]*/g) ?? []
  // 从证据里**深度收集**所有出现过的数字（含千分位写法），
  // 比手工列举字段可靠：加一个字段不用改测试
  const known = new Set()
  const collect = (v) => {
    if (v == null) return
    if (typeof v === 'number') {
      known.add(String(v))
      known.add(Number(v).toLocaleString('en-US'))
      return
    }
    if (typeof v === 'string') {
      for (const m of v.match(/\d[\d,]*/g) ?? []) {
        known.add(m)
        known.add(m.replace(/,/g, ''))
      }
      return
    }
    if (Array.isArray(v)) { v.forEach(collect); return }
    if (typeof v === 'object') { Object.values(v).forEach(collect) }
  }
  collect(e1.count); collect(e1.total); collect(e1.withWiki)
  collect(e1.levels); collect(e1.areas); collect(e1.families)
  collect(e1.growth); collect(e1.busiest); collect(e1.absent)
  // 百分比、等级号、年份这类不在集合里，单独放行
  const suspicious = [...new Set(nums)].filter((x) => {
    const plain = x.replace(/,/g, '')
    if (known.has(x) || known.has(plain)) return false
    if (Number(plain) <= 6) return false            // 濒危等级号
    return true
  })
  check('没有来源不明的数字', suspicious.length === 0,
    suspicious.length ? suspicious.join(', ') : `${new Set(nums).size} 个数全部可追溯`)

  /* ---------- 3. 没有命中的情况 ---------- */
  console.log('\n=== 3. 筛空时的表现 ===')
  // 注意：applyIntent 有白名单，不存在的语系/等级会被丢掉（这是对的）。
  // 想真的筛空，要用一个不存在的地名查询。
  s.applyIntent({ nameQuery: 'zzzzqqq' })
  const e0 = pack(s.filtered)
  const a0 = composeAnswer({
    question: '完全不存在的条件', intent: null, evidence: e0, lang: 'zh',
  })
  check('命中数为 0', e0.count === 0)
  check('不崩、且明确说没有命中',
    !!a0.title && /没有命中|No match/.test(a0.title), a0.title)
  check('给出了可操作的建议（放宽条件）',
    /放宽|relax/.test(a0.lead), a0.lead.slice(0, 40))

  /* ---------- 4. 中文 / 英文 ---------- */
  console.log('\n=== 4. 中英双语 ===')
  s.applyIntent(i1)
  const e2 = pack(s.filtered)
  const en = composeAnswer({ question: 'critically endangered', intent: i1, evidence: e2, lang: 'en' })
  check('英文答案不含中文字符',
    !/[\u4e00-\u9fa5]/.test(en.title + en.lead + en.bullets.join('')),
    en.title)

} finally {
  h.cleanup()
}

/* ---------- 5. 端点：没有密钥时要优雅降级 ---------- */
// 放在 harness 清理之后：harness 会用替身替换 globalThis.fetch
console.log('\n=== 5. /api/nl/answer 的兜底 ===')
try {
  const res = await fetch('http://127.0.0.1:5173/api/nl/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: 'x', intent: null, evidence: { count: 1 }, lang: 'zh' }),
  })
  const d = await res.json()
  check('端点可用，且无密钥时返回 no-key（前端会退回本地合成）',
    d.ok === true || d.reason === 'no-key', JSON.stringify(d).slice(0, 90))
} catch (err) {
  check('端点可用', false, String(err))
}

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
