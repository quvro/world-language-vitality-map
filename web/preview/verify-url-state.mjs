/**
 * 验证 URL 状态分享：编码 → 解码 → 状态是否一致。
 *
 * 两条实现约束（都踩过）：
 *   · 不能用手搓的 mock store —— applyIntent 里的白名单校验才是要验的部分。
 *   · **不能用 Vite 的 ssrLoadModule**：它加载 vite.config.ts 时要 esbuild 起子进程，
 *     沙箱直接 `spawn EPERM`（这是既定边界，不该反复重试）。
 *     改用 TypeScript 自带的 `transpileModule` —— 它在本进程内跑，不起子进程。
 *     转译的是**真实源码**，只把 `@/` 别名改写成相对路径。
 */
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)
const ts = require('typescript')

const WEB = path.resolve('web')
const SRC = path.join(WEB, 'src')
const DATA = path.resolve('data/processed')
const TMP = path.join(WEB, '.verify-tmp')

/** 转译一个 TS 文件到 TMP，并把 @/ 别名改写成相对路径 */
function emit(rel, outName, depth = 0) {
  const out = ts.transpileModule(readFileSync(path.join(SRC, rel), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: false,
    },
  }).outputText
  const up = depth > 0 ? '../'.repeat(depth) : './'
  const fixed = out.replace(/from ['"]@\/([\w./-]+)['"]/g, (_m, p) => `from '${up}${p}.js'`)
  writeFileSync(path.join(TMP, outName), fixed)
}

rmSync(TMP, { recursive: true, force: true })
mkdirSync(path.join(TMP, 'stores'), { recursive: true })
emit('terms.ts', 'terms.js')
emit('types.ts', 'types.js')
emit('stores/dataset.ts', 'stores/dataset.js', 1)
emit('urlState.ts', 'urlState.js')

// store 的 loadJson 会 fetch('/data/processed/xxx.json')，改成读磁盘
globalThis.fetch = async (url) => {
  const file = path.join(DATA, String(url).replace(/^\/data\/processed\//, ''))
  try {
    const text = readFileSync(file, 'utf8')
    return { ok: true, status: 200, json: async () => JSON.parse(text) }
  } catch {
    return { ok: false, status: 404 }
  }
}
globalThis.location = { origin: 'http://127.0.0.1:5173', pathname: '/', search: '' }

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

// pinia 必须与 store 模块走**同一条** ESM 路径加载。
// 用 require 拿 CJS 版、store 里 import ESM 版 → 两个模块实例 → setActivePinia 不生效。
const { createPinia, setActivePinia } = await import('pinia')
// Windows 下动态 import 必须是 file:// URL，否则报 ERR_UNSUPPORTED_ESM_URL_SCHEME
const load = (rel) => import(pathToFileURL(path.join(TMP, rel)).href)
const { useDataset } = await load('stores/dataset.js')
const { toQuery, applyQuery, shareUrl } = await load('urlState.js')

const freshStore = async () => {
  setActivePinia(createPinia())
  const s = useDataset()
  await s.load()
  return s
}

try {
  const s = await freshStore()
  console.log(`  数据已加载：${s.langs.length} 门语言，${s.months.length} 个月份`)

  /* ---------- 1. 默认状态应该是干净的 URL ---------- */
  console.log('\n=== 1. 未做任何操作时不应产生参数 ===')
  const emptyQ = toQuery(s)
  check('默认状态编码为空串', emptyQ === '', JSON.stringify(emptyQ))

  /* ---------- 2. 往返一致 ---------- */
  console.log('\n=== 2. 往返：设置状态 → 编码 → 解码 → 是否一致 ===')
  const fam = s.familyList[0].family
  const fid = s.matrix.feature_ids[0]
  Object.assign(s, {
    activeView: 'endanger',
    macroAreas: ['Africa'],
    families: [fam],
    search: '语',
    featureFilter: { featureId: fid, value: null },
    growthMin: 0,
    wikiOnly: true,
    minFeatures: 100,
    endangermentLevels: [5, 6],
    selected: s.langs[0].wals_id,
    comparisonSet: [s.langs[1].wals_id],
    monthIndex: 40,
    colorBy: 'trend',
    sizeMode: 'absolute',
    showVitality: false,
    hideUnselected: true,
    lang: 'en',
  })

  const q = toQuery(s)
  console.log(`  编码后（${q.length} 字符）:`)
  console.log('    ?' + q)

  const s2 = await freshStore()
  const applied = applyQuery(s2, q)
  check('applyQuery 报告已应用', applied === true)
  check('activeView', s2.activeView === s.activeView, s2.activeView)
  check('macroAreas', JSON.stringify(s2.macroAreas) === JSON.stringify(s.macroAreas))
  check('families', JSON.stringify(s2.families) === JSON.stringify(s.families))
  check('search', s2.search === s.search)
  check('featureFilter', JSON.stringify(s2.featureFilter) === JSON.stringify(s.featureFilter))
  check('growthMin', s2.growthMin === s.growthMin)
  check('wikiOnly', s2.wikiOnly === s.wikiOnly)
  check('minFeatures', s2.minFeatures === s.minFeatures)
  check('endangermentLevels', JSON.stringify(s2.endangermentLevels) === JSON.stringify(s.endangermentLevels))
  check('selected', s2.selected === s.selected)
  check('comparisonSet', JSON.stringify(s2.comparisonSet) === JSON.stringify(s.comparisonSet))
  check('monthIndex', s2.monthIndex === s.monthIndex)
  check('colorBy', s2.colorBy === s.colorBy)
  check('sizeMode', s2.sizeMode === s.sizeMode)
  check('showVitality', s2.showVitality === s.showVitality)
  check('hideUnselected', s2.hideUnselected === s.hideUnselected)
  check('lang', s2.lang === s.lang)

  const q2 = toQuery(s2)
  check('二次编码完全一致（幂等）', q2 === q)
  check('筛选命中的语言数一致',
    s2.filtered.length === s.filtered.length, `${s.filtered.length} vs ${s2.filtered.length}`)

  /* ---------- 3. 坏链接不能把界面搞崩 ---------- */
  console.log('\n=== 3. 手改坏了的链接 ===')
  const s3 = await freshStore()
  let threw = null
  try {
    applyQuery(s3, 'v=nonsense&m=abc&end=99,0&fam=不存在的语系&ff=NOPE&sm=xxx&cb=yyy&gmin=zzz&lang=fr')
  } catch (e) { threw = e }
  check('不抛异常', threw === null, threw ? String(threw) : '')
  check('非法视图被忽略', s3.activeView === 'map', s3.activeView)
  // 默认月份是**最后一个月**（不是 0），所以"被忽略"意味着保持默认值
  check('非法月份被忽略（保持默认的末月）',
    s3.monthIndex === s3.months.length - 1, `${s3.monthIndex} / ${s3.months.length - 1}`)
  check('非法濒危等级被过滤', s3.endangermentLevels.length === 0, JSON.stringify(s3.endangermentLevels))
  check('不存在的语系被丢弃（走 applyIntent 白名单）', s3.families.length === 0, JSON.stringify(s3.families))
  check('不存在的特征被丢弃', s3.featureFilter === null, JSON.stringify(s3.featureFilter))
  check('非法 sizeMode / colorBy / lang 被忽略',
    s3.sizeMode === 'relative' && s3.colorBy === 'macroarea' && s3.lang === 'zh')

  /* ---------- 4. 月份越界要夹住 ---------- */
  console.log('\n=== 4. 月份越界 ===')
  const s4 = await freshStore()
  applyQuery(s4, 'm=99999')
  check('超出范围的月份被夹到最后一格',
    s4.monthIndex === s4.months.length - 1, `${s4.monthIndex} / ${s4.months.length - 1}`)
  const s5 = await freshStore()
  applyQuery(s5, 'm=-5')
  check('负数月份被夹到 0', s5.monthIndex === 0, String(s5.monthIndex))

  /* ---------- 5. shareUrl 与长度 ---------- */
  console.log('\n=== 5. shareUrl 与链接长度 ===')
  const u = shareUrl(s)
  check('是绝对地址且带参数', u.startsWith('http://127.0.0.1:5173/?'))
  console.log('    ' + u.slice(0, 112) + (u.length > 112 ? ' …' : ''))

  const s6 = await freshStore()
  s6.macroAreas = ['Africa']
  s6.endangermentLevels = [5]
  const short = toQuery(s6)
  console.log(`    两个条件: ?${short}  (${short.length} 字符)`)
  check('常见场景的查询串 < 120 字符', short.length < 120, String(short.length))
  check('全量状态的查询串 < 400 字符', q.length < 400, String(q.length))
} finally {
  rmSync(TMP, { recursive: true, force: true })
}

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
