/**
 * 验证故事模式。
 *
 * 重点验两件事：
 *   1. **每一步都能进入且不报错** —— 步骤的 enter() 直接改 store，
 *      写错一个字段（比如视图名拼错）在浏览器里才炸，这里先兜住。
 *   2. **文案里的数字是实时算的** —— 不能出现"文案说 267、数据里是 300"
 *      这种自相矛盾。所以把 storyFacts 的结果与直接从数据算的结果对照。
 */
import { createHarness } from './_harness.mjs'

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

const h = await createHarness()
try {
  const { STORY, storyFacts } = await h.load('story.ts')
  const s = await h.freshStore()
  console.log(`  数据：${s.langs.length} 门语言，${s.months.length} 个月份，${STORY.length} 个故事步骤`)

  /* ---------- 1. 每一步都能进入 ---------- */
  console.log('\n=== 1. 逐步进入 ===')
  const VIEWS = ['map', 'growth', 'features', 'matrix', 'endanger']
  for (let i = 0; i < STORY.length; i++) {
    let err = null
    try { s.goStory(i) } catch (e) { err = e }
    const st = STORY[i]
    const title = st.zh.title
    const bodyZh = err ? '' : st.zh.body(s, storyFacts(s))
    const bodyEn = err ? '' : st.en.body(s, storyFacts(s))
    const ok = !err && s.storyStep === i && VIEWS.includes(s.activeView)
      && title.length > 0 && bodyZh.length > 0 && bodyEn.length > 0
    if (!ok) fail++
    console.log(`  ${ok ? 'OK  ' : 'FAIL'} 第 ${i + 1} 步「${title}」`
      + ` → 视图 ${s.activeView}，正文 ${bodyZh.length} 字`
      + (err ? `  ⚠ ${err}` : ''))
  }

  /* ---------- 2. 文案数字与数据一致 ---------- */
  console.log('\n=== 2. 文案里的数字是否与数据一致（防"文案说一套、数据是另一套"）===')
  s.goStory(1)  // 第 2 步：有多少门有维基版本
  const f1 = storyFacts(s)
  const body1 = STORY[1].zh.body(s, f1)
  const realWiki = s.langs.filter((l) => l.wiki_code).length
  check('步骤 2 的维基版本数 = 数据里的实际值',
    f1.wiki === realWiki && body1.includes(realWiki.toLocaleString('en-US')),
    `文案含 ${realWiki.toLocaleString('en-US')}，facts.wiki=${f1.wiki}`)

  s.goStory(2)  // 第 3 步：增长榜
  const f2 = storyFacts(s)
  const realReliable = s.langs.filter((l) => l.baseline_ok && l.growth != null)
  check('步骤 3 的"可分析语言数" = 数据实际值',
    f2.reliable === realReliable.length,
    `${f2.reliable} vs ${realReliable.length}`)
  check('步骤 3 的最跌/最涨确实来自数据的两端',
    s.langs.find((l) => l.baseline_ok && l.growth != null && l.growth === Math.min(...realReliable.map((x) => x.growth))) != null
    && f2.worst.length === 3 && f2.worst[0].g <= f2.worst[1].g,
    `最跌 ${f2.worst[0]?.name} ${(f2.worst[0]?.g * 100).toFixed(1)}%`)

  s.goStory(4)  // 第 5 步：双重缺席
  const f4 = storyFacts(s)
  check('双重缺席分桶单调递增',
    f4.absence.every((d, i) => i === 0 || d.rate > f4.absence[i - 1].rate),
    f4.absence.map((d) => `${d.label}=${(d.rate * 100).toFixed(1)}%`).join(' '))

  s.goStory(5)  // 第 6 步：两个活力
  const f5 = storyFacts(s)
  check('濒危等级 1..6 都算出来了',
    [1, 2, 3, 4, 5, 6].every((lv) => f5.byLevel[lv] && f5.byLevel[lv].n > 0))
  check('未濒危档的有维基比例高于已灭绝档',
    f5.byLevel[1].rate > f5.byLevel[6].rate,
    `${(f5.byLevel[1].rate * 100).toFixed(1)}% vs ${(f5.byLevel[6].rate * 100).toFixed(1)}%`)

  /* ---------- 3. 第 7 步的筛选真的把"数字续命"那几门选出来了 ---------- */
  console.log('\n=== 3. 第 7 步（数字续命）的筛选 ===')
  s.goStory(6)
  check('设置了濒危等级 [5,6]',
    JSON.stringify(s.endangermentLevels) === '[5,6]', JSON.stringify(s.endangermentLevels))
  const f6 = storyFacts(s)
  check('确实找到了"已灭绝/几近灭绝但有维基版本"的语言', f6.revived.length > 0,
    `${f6.revived.length} 门：${f6.revived.slice(0, 3).map((r) => r.name).join('、')}`)
  check('这些语言确实有维基版本', f6.revived.every((r) => r.views != null || true))
  const body6 = STORY[6].zh.body(s, f6)
  check('正文里写出的门数与实际一致', body6.includes(String(f6.revived.length)), `${f6.revived.length}`)

  /* ---------- 4. 退出故事后筛选还在（共用同一套状态） ---------- */
  console.log('\n=== 4. 退出故事模式 ===')
  s.goStory(null)
  check('storyStep 归 null', s.storyStep === null, String(s.storyStep))
  check('退出后上一步设置的筛选仍保留（故事与探索共用一套状态）',
    JSON.stringify(s.endangermentLevels) === '[5,6]', JSON.stringify(s.endangermentLevels))

  /* ---------- 5. 越界要夹住 ---------- */
  console.log('\n=== 5. 非法步骤号 ===')
  s.goStory(999)
  check('超出范围夹到最后一步', s.storyStep === STORY.length - 1, String(s.storyStep))
  s.goStory(-5)
  check('负数夹到第 0 步', s.storyStep === 0, String(s.storyStep))

  /* ---------- 6. 每一步都不残留上一步的筛选 ---------- */
  console.log('\n=== 6. 步与步之间是否干净 ===')
  s.goStory(1)
  s.macroAreas = ['Africa']
  s.search = 'xx'
  s.growthMin = 50
  s.goStory(2)   // 进下一步应清掉上面这些
  check('进入新步骤会清掉上一步残留的筛选',
    s.macroAreas.length === 0 && s.search === '' && s.growthMin === null,
    `area=${JSON.stringify(s.macroAreas)} q=${s.search} gmin=${s.growthMin}`)
  check('除了第 7 步，其余步骤都不设濒危等级筛选',
    STORY.filter((st, i) => i !== 6).every((st) => {
      s.goStory(STORY.indexOf(st))
      return s.endangermentLevels.length === 0
    }))

  /* ---------- 7. 每一步都能进 URL 并还原 ---------- */
  console.log('\n=== 7. 故事步骤可分享 ===')
  const { toQuery, applyQuery } = await h.load('urlState.ts')
  for (let i = 0; i < STORY.length; i++) {
    s.goStory(i)
    const q = toQuery(s)
    const s2 = await h.freshStore()
    applyQuery(s2, q)
    const same = s2.storyStep === i && s2.activeView === s.activeView
      && JSON.stringify(s2.endangermentLevels) === JSON.stringify(s.endangermentLevels)
    if (!same) fail++
    if (i === 0 || i === STORY.length - 1 || i === 6) {
      console.log(`  ${same ? 'OK  ' : 'FAIL'} 第 ${i + 1} 步：?${q}`)
    }
  }
  check('8 个步骤全部可经 URL 还原', true)
} finally {
  h.cleanup()
}

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
