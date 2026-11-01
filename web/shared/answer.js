/**
 * 自然语言问答的第二段：**检索 + 组织答案**。
 *
 * 职责划分是刻意的：
 *   · 意图解析（把话变成筛选条件）→ shared/intent.js，可以由大模型做
 *   · **检索**（从当前数据集里数出事实）→ 本文件，永远在前端算
 *   · 措辞（把事实写成句子）→ 可以是本地模板，也可以交给大模型
 *
 * 为什么检索一定要在前端：这样答案里的每个数字和视图里的数字**必然是同一个来源**，
 * 不会出现"模型编了个数"。发给大模型的只有算好的证据包，它只负责把证据说成人话。
 * 没有密钥时用 composeAnswer 兜底，整条链路依然可用、可演示。
 */

const pct = (x) => `${(x * 100).toFixed(1)}%`
const num = (n) => Number(n).toLocaleString('en-US')

/** 中位数 */
function median(xs) {
  if (!xs.length) return null
  const a = [...xs].sort((x, y) => x - y)
  const m = a.length >> 1
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2
}

/**
 * 从**已筛选的结果**里算出证据包。
 * @param rows      当前命中的语言行（store.filtered）
 * @param total     全库语言数
 * @param ebw       wals_id → 濒危等级
 * @param featCount wals_id → 已记录的特征数
 * @param label     (row) => 显示名
 */
export function buildEvidence({ rows, total, ebw = {}, featCount = {}, label }) {
  const n = rows.length
  const withWiki = rows.filter((r) => r.wiki_code)
  const growths = rows.filter((r) => r.baseline_ok && r.growth != null)
    .map((r) => r.growth)

  // 语区 / 语系分布
  const byArea = {}
  const byFam = {}
  for (const r of rows) {
    const a = r.macroarea || '—'
    byArea[a] = (byArea[a] || 0) + 1
    const f = r.family || '—'
    byFam[f] = (byFam[f] || 0) + 1
  }
  const top = (obj, k = 4) =>
    Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, k)
      .map(([name, count]) => ({ name, n: count }))

  // 濒危等级分布（1..6）
  const lvCount = {}
  for (const r of rows) {
    const lv = ebw[r.wals_id]
    if (lv) lvCount[lv] = (lvCount[lv] || 0) + 1
  }

  const byViews = rows.filter((r) => (r.views_recent ?? 0) > 0)
    .sort((a, b) => (b.views_recent ?? 0) - (a.views_recent ?? 0))
  const byFeatures = rows.slice()
    .sort((a, b) => (featCount[b.wals_id] ?? 0) - (featCount[a.wals_id] ?? 0))

  return {
    count: n,
    total,
    share: total ? n / total : 0,
    withWiki: withWiki.length,
    wikiShare: n ? withWiki.length / n : 0,
    areas: top(byArea),
    families: top(byFam),
    levels: Object.entries(lvCount).sort((a, b) => a[0] - b[0])
      .map(([lv, c]) => ({ lv: Number(lv), n: c })),
    growth: {
      n: growths.length,
      median: median(growths),
      up: growths.filter((g) => g > 0).length,
      down: growths.filter((g) => g < 0).length,
    },
    // 关注度最高的三门（有维基版本才有浏览量）
    busiest: byViews.slice(0, 3).map((r) => ({
      name: label(r), views: Math.round(r.views_recent ?? 0),
      growth: r.growth ?? null,
    })),
    // 记录最完整但**没有**数字入口的（"双重缺席"最典型的例子）
    absent: byFeatures.filter((r) => !r.wiki_code).slice(0, 3).map((r) => ({
      name: label(r), features: featCount[r.wals_id] ?? 0,
    })),
  }
}

/**
 * 本地合成答案：没有大模型密钥时用它，保证链路可用。
 * 输出结构化（标题 / 一句话结论 / 若干条要点 / 注意事项），由面板负责渲染。
 */
export function composeAnswer({ question, intent, evidence: e, lang = 'zh' }) {
  const zh = lang === 'zh'
  if (!e.count) {
    return {
      title: zh ? '没有命中的语言' : 'No match',
      lead: zh
        ? '当前条件下数据集里没有任何一门语言符合。可以放宽一个条件再试，或看看下面的建议。'
        : 'No language in the dataset satisfies all conditions. Try relaxing one.',
      bullets: [],
      caveats: [],
    }
  }

  const bullets = []
  const L = (v) => Math.round(Number(v))

  if (zh) {
    if (e.levels.length) {
      const parts = e.levels.map((x) => `等级 ${x.lv} 有 ${num(x.n)} 门`)
      bullets.push(`**濒危等级分布**：${parts.join('，')}。`)
    }
    if (e.areas.length) {
      bullets.push(`**语区**：${e.areas.map((a) => `${a.name} ${num(a.n)} 门`).join('、')}。`)
    }
    if (e.families.length) {
      bullets.push(`**语系**：${e.families.map((f) => `${f.name} ${num(f.n)} 门`).join('、')}。`)
    }
    if (e.growth.n) {
      const m = e.growth.median
      bullets.push(
        `**十年变化**：${num(e.growth.n)} 门基线可靠，中位数 ${m >= 0 ? '+' : ''}${pct(m)}；`
        + `在涨 ${num(e.growth.up)} 门，在退 ${num(e.growth.down)} 门。`,
      )
    }
    if (e.busiest.length) {
      bullets.push('**关注度最高**：'
        + e.busiest.map((b) => `${b.name}（月阅读 ${num(b.views)}）`).join('、') + '。')
    }
    if (e.absent.length) {
      bullets.push('**记录最完整却没有数字入口**：'
        + e.absent.map((b) => `${b.name}（${b.features} 个特征）`).join('、')
        + ' —— 这正是"双重缺席"的典型。')
    }
  } else {
    if (e.levels.length) {
      bullets.push(`**Endangerment**: ${e.levels.map((x) => `level ${x.lv}: ${num(x.n)}`).join(', ')}.`)
    }
    if (e.areas.length) {
      bullets.push(`**Areas**: ${e.areas.map((a) => `${a.name} ${num(a.n)}`).join(', ')}.`)
    }
    if (e.families.length) {
      bullets.push(`**Families**: ${e.families.map((f) => `${f.name} ${num(f.n)}`).join(', ')}.`)
    }
    if (e.growth.n) {
      bullets.push(`**Ten-year change**: ${num(e.growth.n)} with a reliable baseline, `
        + `median ${e.growth.median >= 0 ? '+' : ''}${pct(e.growth.median)}.`)
    }
  }

  const caveats = []
  if (zh) {
    caveats.push(`命中 ${num(e.count)} 门，占全库 ${num(e.total)} 门的 ${pct(e.share)}；`
      + `其中 ${num(e.withWiki)} 门（${pct(e.wikiShare)}）有维基百科版本。`)
    if (e.withWiki === 0) {
      caveats.push('这一批语言全部没有维基百科版本 —— 它们在时间序列与浏览量视图里会呈现为「缺席」，而不是「0」。')
    }
    if (e.count > 300) {
      caveats.push('命中的语言较多，逐条看意义有限；建议再加一个条件缩到几十门以内。')
    }
  } else {
    caveats.push(`${num(e.count)} of ${num(e.total)} languages (${pct(e.share)}); `
      + `${num(e.withWiki)} (${pct(e.wikiShare)}) have a Wikipedia edition.`)
  }

  return {
    title: zh ? `命中 ${num(e.count)} 门语言` : `${num(e.count)} languages match`,
    lead: zh
      ? `在 ${num(e.total)} 门语言里，有 ${num(e.count)} 门符合「${intentText(intent, zh) || question}」这个条件。`
      : `Of ${num(e.total)} languages, ${num(e.count)} match “${intentText(intent, false) || question}”.`,
    bullets,
    caveats,
  }
}

/** 把意图写成人话，用于标题句 */
export function intentText(intent, zh = true) {
  if (!intent) return ''
  const parts = []
  const sep = { min: 0 }
  void sep
  if (intent.macroAreas?.length) parts.push(intent.macroAreas.join('、'))
  if (intent.families?.length) parts.push(intent.families.join('、'))
  if (intent.endangermentLevels?.length) {
    parts.push((zh ? '濒危等级 ' : 'endangerment ')
      + intent.endangermentLevels.join('/'))
  }
  if (intent.wikiOnly) parts.push(zh ? '有维基版本' : 'with Wikipedia')
  if (intent.growthMin != null) {
    parts.push(`${zh ? '增长 ≥ ' : 'growth ≥ '}${pct(intent.growthMin)}`)
  }
  if (intent.growthMax != null) {
    parts.push(`${zh ? '增长 ≤ ' : 'growth ≤ '}${pct(intent.growthMax)}`)
  }
  if (intent.minFeatures != null) {
    parts.push(`${zh ? '记录特征 ≥ ' : 'features ≥ '}${intent.minFeatures}`)
  }
  if (intent.featureId) {
    parts.push(intent.featureValue
      ? `${intent.featureId}=${intent.featureValue}`
      : intent.featureId)
  }
  if (intent.nameQuery) parts.push(`“${intent.nameQuery}”`)
  return parts.join(' · ')
}
