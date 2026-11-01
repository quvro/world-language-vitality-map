/**
 * 端到端实测（需要真实密钥，不是 CI 脚本）：问一句 → 大模型解析意图 →
 * 前端检索证据 → 大模型措辞 → 打印完整答案。
 *
 * 注意：harness 会把 globalThis.fetch 换成读磁盘的替身，
 * 所以必须先抓一份**真实** fetch，HTTP 请求才打得出去。
 */
import { createHarness } from './_harness.mjs'

const realFetch = globalThis.fetch
const Q = process.argv[2] || '非洲语区里语序是 SOV 且在增长的语言'
const BASE = 'http://127.0.0.1:5173'

const h = await createHarness()
try {
  const { buildEvidence, composeAnswer } = await h.load('answer.js')
  const s = await h.freshStore()
  const ctx = { families: s.familyList.map((f) => f.family), features: [] }

  const r1 = await realFetch(`${BASE}/api/nl`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: Q, context: ctx }),
  })
  const d1 = await r1.json()
  console.log('问题：', Q)
  console.log('① 意图解析 ok =', d1.ok, ' 来源 =', d1.ok ? '大模型' : d1.reason)
  console.log('   意图 =', JSON.stringify(d1.intent ?? null).slice(0, 220))

  s.applyIntent(d1.intent ?? null)
  const evidence = buildEvidence({
    rows: s.filtered, total: s.langs.length,
    ebw: s.endangermentByWals, featCount: s.featureCount,
    label: (r) => r.name,
  })
  console.log('② 检索：命中', evidence.count, '/', evidence.total,
    ' 有维基', evidence.withWiki, ' 等级分布', JSON.stringify(evidence.levels))

  const r2 = await realFetch(`${BASE}/api/nl/answer`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: Q, intent: d1.intent, evidence, lang: 'zh' }),
  })
  const d2 = await r2.json()
  console.log('③ 措辞 ok =', d2.ok, d2.model ? `（${d2.model}）` : `（${d2.reason}）`)
  if (d2.ok) {
    const a = d2.answer
    console.log('\n—— 大模型写的答案 ——')
    console.log('  ' + a.title)
    console.log('  ' + a.lead)
    for (const b of a.bullets) console.log('  · ' + b.replace(/\*\*/g, ''))
    for (const c of a.caveats) console.log('  ⚠ ' + c)
  }
  const local = composeAnswer({ question: Q, intent: d1.intent, evidence, lang: 'zh' })
  console.log('\n—— 本地兜底（无 key 时用它）——')
  console.log('  ' + local.title)
  for (const b of local.bullets.slice(0, 3)) console.log('  · ' + b.replace(/\*\*/g, ''))
} finally {
  h.cleanup()
}
