/**
 * 自然语言 → 结构化意图。**前后端共用**（Vite 中间件与浏览器都 import 这个文件），
 * 避免两边的字段定义漂移。
 *
 * 设计要点：
 *   · 模型只负责"把话翻译成筛选条件"，不负责算数 —— 统计一律在前端做，
 *     这样解释里的数字必然与实际视图一致，不会出现"模型编了个数"。
 *   · 没有 API Key 时用本地规则解析器兜底，功能不中断（课程演示不能因为没网就废）。
 */

/** 六大语区（与地图图例一致） */
export const MACRO_AREAS = [
  'Africa', 'Eurasia', 'Papunesia',
  'North America', 'South America', 'Australia',
]

/** 喂给大模型的 function 参数 schema */
export const INTENT_SCHEMA = {
  type: 'object',
  properties: {
    macroAreas: {
      type: 'array',
      items: { type: 'string', enum: MACRO_AREAS },
      description: '按语区筛选，可多选',
    },
    families: {
      type: 'array',
      items: { type: 'string' },
      description: '按 WALS 语系英文名筛选，必须使用上下文给出的语系名，可多选',
    },
    nameQuery: {
      type: 'string',
      description: '语言名称关键词（中文或英文），例如「班图」「Arabic」',
    },
    featureId: {
      type: 'string',
      description: 'WALS 语法特征 ID，例如 81A（主宾动语序）、13A（声调）。必须来自上下文给出的特征列表',
    },
    featureValue: {
      type: 'string',
      description: '上一条特征的具体取值，例如 81A 的 SOV / SVO / VSO；不填表示"只需要有该特征的数据"',
    },
    growthMin: {
      type: 'number',
      description: '十年浏览量增长率下限，单位百分数。0 表示「在增长」，-100 表示「跌了一半以上」',
    },
    growthMax: {
      type: 'number',
      description: '十年浏览量增长率上限，单位百分数。0 表示「在衰退」',
    },
    wikiOnly: {
      type: 'boolean',
      description: '是否只保留拥有维基百科版本的语言',
    },
    minFeatures: {
      type: 'number',
      description: '该语言在 WALS 中至少被收录多少个语法特征（数据完整度），常用 100',
    },
    period: {
      type: 'string',
      description: '把时间轴定位到某年或某月，格式 YYYY 或 YYYYMM，例如 2018 或 201803',
    },
    endangermentLevels: {
      type: 'array',
      items: { type: 'integer', enum: [1, 2, 3, 4, 5, 6] },
      description:
        'UNESCO 濒危等级筛选。1=安全 2=脆弱 3=明确濒危 4=严重濒危 5=极度濒危 6=已灭绝。' +
        '用户说「濒危语言」时填 [2,3,4,5,6]；说「极度濒危」时填 [5]。',
    },
    explanation: {
      type: 'string',
      description: '用一句话向用户复述你理解到的筛选意图，使用与用户提问相同的语言',
    },
  },
  required: [],
}

/* ------------------------------------------------------------------ 本地解析 */

/** 语区的中英关键词 */
const AREA_WORDS = {
  Africa: ['非洲', 'africa'],
  Eurasia: ['欧亚', '欧洲', '亚洲', 'eurasia', 'europe', 'asia'],
  Papunesia: ['巴布亚', '新几内亚', 'papunesia', 'papua'],
  'North America': ['北美', '北美洲', 'north america'],
  'South America': ['南美', '南美洲', 'south america'],
  Australia: ['澳洲', '澳大利亚', 'australia'],
}

/** 语系的中英关键词（覆盖语言数最多的那些） */
const FAMILY_WORDS = {
  'Indo-European': ['印欧', 'indo-european', 'indoeuropean'],
  'Sino-Tibetan': ['汉藏', 'sino-tibetan'],
  'Niger-Congo': ['尼日尔-刚果', '尼日尔刚果', 'niger-congo'],
  Austronesian: ['南岛', 'austronesian'],
  'Afro-Asiatic': ['亚非', 'afro-asiatic'],
  'Pama-Nyungan': ['帕马', 'pama-nyungan'],
  'Trans-New Guinea': ['跨新几内亚', 'trans-new guinea'],
  Altaic: ['阿尔泰', 'altaic'],
  Uralic: ['乌拉尔', 'uralic'],
  Dravidian: ['达罗毗荼', 'dravidian'],
  'Tai-Kadai': ['侗台', 'tai-kadai'],
  'Hmong-Mien': ['苗瑶', 'hmong-mien'],
  Turkic: ['突厥', 'turkic'],
  Mongolic: ['蒙古语系', 'mongolic'],
  Mayan: ['玛雅', 'mayan'],
  Quechuan: ['克丘亚', 'quechuan'],
  'Austro-Asiatic': ['南亚语系', 'austro-asiatic'],
  'Uto-Aztecan': ['犹他-阿兹特克', 'uto-aztecan'],
  Algic: ['阿尔冈昆', 'algic'],
}

/** 语序特征 81A 的取值关键词 */
const WORD_ORDER = {
  SOV: ['sov', '主宾动'],
  SVO: ['svo', '主动宾'],
  VSO: ['vso', '动主宾'],
  VOS: ['vos', '动宾主'],
  OVS: ['ovs', '宾动主'],
  OSV: ['osv', '宾主动'],
}

/** 少数"特征 + 取值"的固定搭配（规则解析很难泛化，所以只做几个高频的） */const FEATURE_PATTERNS = [
  { re: /声调|有声调|tone/i, id: '13A', value: null, hint: '声调' },
  { re: /文字系统|有文字|writing system/i, id: '141A', value: null, hint: '文字系统' },
  { re: /小舌辅音|uvular/i, id: '6A', value: null, hint: '小舌辅音' },
  { re: /格标记|有格|case marking/i, id: '49A', value: null, hint: '格的数量' },
  { re: /性范畴|有性别|gender/i, id: '30A', value: null, hint: '性范畴的数量' },
  { re: /关系从句|relative clause/i, id: '90A', value: null, hint: '关系从句与名词的语序' },
  { re: /重叠|reduplication/i, id: '27A', value: null, hint: '重叠' },
]

/**
 * 关键词命中。
 *
 * ASCII 关键词**必须按词边界匹配**，不能简单 includes ——
 * 实测 "Indo-European" 会被 "europe" 命中、"Austro-Asiatic" 会被 "asia" 命中，
 * 于是「印欧语系中有声调的语言」被误加上了「语区=欧亚」。
 * 中文没有词边界概念，仍旧用 includes。
 */
/** UNESCO 濒危等级关键词。注意"濒危"是 3/4/5 的公共子串，必须先匹配具体档位。 */
const ENDANGER_WORDS = {
  1: ['安全', 'safe'],
  2: ['脆弱', 'vulnerable'],
  3: ['明确濒危', 'definitely endangered'],
  4: ['严重濒危', 'severely endangered'],
  5: ['极度濒危', '极危', 'critically endangered'],
  6: ['已灭绝', '灭绝', 'extinct'],
}
/** 只说了"濒危"没指档位时，理解为名录里的任意濒危档 */
const ENDANGER_ANY = [2, 3, 4, 5, 6]

function hitAny(text, words) {
  return words.some((w) => {
    if (/^[\x20-\x7e]+$/.test(w)) {
      const esc = w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      return new RegExp(`\\b${esc}\\b`, 'i').test(text)
    }
    return text.includes(w)
  })
}

/**
 * 本地规则解析器：无需 API Key，覆盖常见问法。
 * 返回与 INTENT_SCHEMA 同构的对象。
 */
export function parseLocal(question, ctx = {}) {
  const raw = String(question || '')
  const q = raw.toLowerCase()
  const out = { explanation: '', _source: 'local' }

  // 语区
  const areas = MACRO_AREAS.filter((a) => hitAny(q, AREA_WORDS[a] || []))
  if (areas.length) out.macroAreas = areas

  // 语系（用上下文里的真实语系名做白名单，避免词典写错）
  const known = new Set(ctx.families || [])
  const fams = Object.keys(FAMILY_WORDS).filter(
    (f) => (!known.size || known.has(f)) && hitAny(q, FAMILY_WORDS[f])
  )
  if (fams.length) out.families = fams

  // 语序（最高频的一类问法）
  const order = Object.keys(WORD_ORDER).find((k) => hitAny(q, WORD_ORDER[k]))
  if (order) {
    out.featureId = '81A'
    out.featureValue = order
  } else {
    const fp = FEATURE_PATTERNS.find((p) => p.re.test(raw))
    if (fp) {
      out.featureId = fp.id
      if (fp.value) out.featureValue = fp.value
    }
  }

  // 增长 / 衰退
  const up = /增长|上升|上涨|在涨|变多|grow|growing|increase|rising/i.test(raw)
  const down = /衰退|下降|下跌|在跌|变少|萎缩|declin|decreas|falling|shrink/i.test(raw)
  if (up && !down) out.growthMin = 0
  else if (down && !up) out.growthMax = 0
  else if (/大跌|暴跌|腰斩|slump|plummet/i.test(raw)) out.growthMax = -50

  // 维基版本
  if (/有维基|有维基百科|有维基版本|with wikipedia|has wikipedia|wikiped/i.test(raw)) {
    out.wikiOnly = true
  }

  // 数据完整度
  const minF = raw.match(/(?:至少|超过|多于)?\s*(\d{2,3})\s*(?:个|条)?\s*特征/)
  if (minF) out.minFeatures = Number(minF[1])
  else if (/数据完整|资料完整|complete data/i.test(raw)) out.minFeatures = 100

  // UNESCO 濒危等级。先匹配具体档位，"濒危"这个公共子串留到最后兜底
  const lv = []
  for (const k of [1, 2, 3, 4, 5, 6]) {
    if (hitAny(q, ENDANGER_WORDS[k])) lv.push(k)
  }
  if (lv.length) {
    out.endangermentLevels = lv
  } else if (hitAny(q, ['濒危', 'endangered', '消失的语言'])) {
    out.endangermentLevels = [...ENDANGER_ANY]
  }

  // 时间定位
  const ym = raw.match(/(20\d{2})\s*年\s*(\d{1,2})\s*月/)
  const y = raw.match(/(20\d{2})\s*年?/)
  if (ym) out.period = `${ym[1]}${String(ym[2]).padStart(2, '0')}`
  else if (y) out.period = y[1]

  // 名称关键词：把引号里的、或「叫/名为」后面的内容当作名字
  const quoted = raw.match(/[「『"']([^」』"']{2,20})[」』"']/)
  const named = raw.match(/(?:叫|名为|名字是|语言名是)\s*([^\s，,。？?]{2,20})/)
  if (quoted) out.nameQuery = quoted[1]
  else if (named) out.nameQuery = named[1]

  return out
}

/* --------------------------------------------------------------- 人类可读化 */

const AREA_ZH = {
  Africa: '非洲', Eurasia: '欧亚', Papunesia: '巴布亚地区',
  'North America': '北美', 'South America': '南美', Australia: '澳洲',
}

/**
 * 把意图翻译成一行行可读条件，用于界面上的「我理解到的条件」。
 * featureName 由调用方传入（它需要特征表），避免这里依赖数据文件。
 */
export function describeIntent(intent, lang = 'zh', featureName = (id) => id) {
  const chips = []
  const zh = lang === 'zh'
  if (!intent) return chips

  if (intent.macroAreas?.length) {
    chips.push({
      key: 'area',
      label: zh ? '语区' : 'Area',
      value: intent.macroAreas.map((a) => (zh ? (AREA_ZH[a] ?? a) : a)).join(zh ? '、' : ', '),
    })
  }
  if (intent.families?.length) {
    chips.push({
      key: 'family',
      label: zh ? '语系' : 'Family',
      value: intent.families.join(zh ? '、' : ', '),
    })
  }
  if (intent.nameQuery) {
    chips.push({ key: 'name', label: zh ? '名称包含' : 'Name contains', value: intent.nameQuery })
  }
  if (intent.featureId) {
    const nm = featureName(intent.featureId)
    chips.push({
      key: 'feature',
      label: zh ? '语法特征' : 'Feature',
      value: intent.featureValue ? `${nm} = ${intent.featureValue}` : nm,
    })
  }
  if (intent.growthMin != null || intent.growthMax != null) {
    const lo = intent.growthMin != null ? `${intent.growthMin}%` : ''
    const hi = intent.growthMax != null ? `${intent.growthMax}%` : ''
    const v = intent.growthMin != null && intent.growthMax != null
      ? `${lo} ~ ${hi}`
      : intent.growthMin != null ? `≥ ${lo}` : `≤ ${hi}`
    chips.push({ key: 'growth', label: zh ? '十年增长' : '10-yr growth', value: v })
  }
  if (intent.wikiOnly) {
    chips.push({ key: 'wiki', label: zh ? '范围' : 'Scope', value: zh ? '仅有维基百科版本' : 'has Wikipedia edition' })
  }
  if (intent.minFeatures) {
    chips.push({
      key: 'minFeatures',
      label: zh ? '数据完整度' : 'Data coverage',
      value: zh ? `≥ ${intent.minFeatures} 个特征` : `≥ ${intent.minFeatures} features`,
    })
  }
  if (intent.period) {
    const p = String(intent.period)
    chips.push({
      key: 'period',
      label: zh ? '定位到' : 'Jump to',
      value: p.length === 6 ? `${p.slice(0, 4)}-${p.slice(4, 6)}` : p,
    })
  }
  if (intent.endangermentLevels?.length) {
    const LV = {
      1: ['安全', 'safe'], 2: ['脆弱', 'vulnerable'],
      3: ['明确濒危', 'definitely endangered'], 4: ['严重濒危', 'severely endangered'],
      5: ['极度濒危', 'critically endangered'], 6: ['已灭绝', 'extinct'],
    }
    chips.push({
      key: 'endanger',
      label: zh ? 'UNESCO 濒危等级' : 'UNESCO status',
      value: intent.endangermentLevels.map((n) => LV[n][zh ? 0 : 1]).join(zh ? '、' : ', '),
    })
  }
  return chips
}

/** 命中数为 0 时给一句有用的提示，而不是干巴巴的"没有结果" */
export function emptyHint(intent, lang = 'zh') {
  const zh = lang === 'zh'
  const relaxed = []
  if (intent?.featureValue) relaxed.push(zh ? '语法特征的取值' : 'the feature value')
  if (intent?.growthMin != null || intent?.growthMax != null) relaxed.push(zh ? '增长区间' : 'the growth range')
  if (intent?.macroAreas?.length) relaxed.push(zh ? '语区' : 'the area')
  if (!relaxed.length) return zh ? '没有符合条件的语言。' : 'No language matches.'
  return zh
    ? `没有语言同时满足这些条件。可以试试放宽：${relaxed.join('、')}。`
    : `No language satisfies all of these. Try relaxing: ${relaxed.join(', ')}.`
}
