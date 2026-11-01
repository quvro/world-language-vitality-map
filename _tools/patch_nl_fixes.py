"""修 4 处：英文 lead 里硬编码了中文意图文本；三处测试自身的问题。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- 1) 真 bug：英文分支里 intentText 的 zh 参数硬编码成了 true
P = "web/shared/answer.js"
s = io.open(P, encoding="utf-8").read()
old = "      : `Of ${num(e.total)} languages, ${num(e.count)} match “${intentText(intent, true) || question}”.`,"
new = "      : `Of ${num(e.total)} languages, ${num(e.count)} match “${intentText(intent, false) || question}”.`,"
if old in s:
    s = s.replace(old, new, 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("  ok   英文 lead 不再混中文（intentText(inent, false)）")
else:
    print("  MISS answer.js 英文 lead")

# ---- 2) 测试脚本：三处修正
P2 = "web/preview/verify-nl-answer.mjs"
t = io.open(P2, encoding="utf-8").read()

# (a) 数字追溯：直接从证据里深度收集所有数字，比手工列举可靠
old_set = t[t.index("  const known = new Set(["):t.index("  function b1(n)")]
new_set = """  // 从证据里**深度收集**所有出现过的数字（含千分位写法），
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
      for (const m of v.match(/\\d[\\d,]*/g) ?? []) {
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
"""
t = t.replace(old_set, new_set, 1)
t = t.replace("""  function b1(n) { return Number(n).toLocaleString('en-US') }
""", "", 1)
t = t.replace("""    ...e1.busiest.map((x) => b1(x.views)),
    ...e1.absent.map((x) => String(x.features)),
  ])
""", "", 1)

# (b) 筛空：语系会被白名单过滤掉，用 nameQuery 才能真的筛空
t = t.replace(
    "  s.applyIntent({ families: ['不存在的语系'], endangermentLevels: [99] })",
    "  // 注意：applyIntent 有白名单，不存在的语系/等级会被丢掉（这是对的）。\n"
    "  // 想真的筛空，要用一个不存在的地名查询。\n"
    "  s.applyIntent({ nameQuery: 'zzzzqqq' })",
    1,
)

# (c) 端点检查要放到 harness 清理**之后**，否则会用到 harness 的 fetch 替身
endpoint_block = t[t.index("  /* ---------- 5. 端点"):t.index("} finally {")]
t = t.replace(endpoint_block, "", 1)
t = t.replace(
    "console.log(`\\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)",
    "/* ---------- 5. 端点：没有密钥时要优雅降级 ---------- */\n"
    "// 放在 harness 清理之后：harness 会用替身替换 globalThis.fetch\n"
    "console.log('\\n=== 5. /api/nl/answer 的兜底 ===')\n"
    "try {\n"
    "  const res = await fetch('http://127.0.0.1:5173/api/nl/answer', {\n"
    "    method: 'POST',\n"
    "    headers: { 'Content-Type': 'application/json' },\n"
    "    body: JSON.stringify({ question: 'x', intent: null, evidence: { count: 1 }, lang: 'zh' }),\n"
    "  })\n"
    "  const d = await res.json()\n"
    "  check('端点可用，且无密钥时返回 no-key（前端会退回本地合成）',\n"
    "    d.ok === true || d.reason === 'no-key', JSON.stringify(d).slice(0, 90))\n"
    "} catch (err) {\n"
    "  check('端点可用', false, String(err))\n"
    "}\n\n"
    "console.log(`\\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)",
    1,
)

io.open(P2, "w", encoding="utf-8").write(t)
print("  ok   测试脚本三处修正（数字深度收集 / 筛空方式 / 端点检查位置）")
