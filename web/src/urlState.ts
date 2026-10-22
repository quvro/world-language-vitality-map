/**
 * 把看板状态同步到 URL —— 让「当前看到的画面」可以分享。
 *
 * 场景：答辩或发给老师时，直接给一条链接，对方打开就是你看到的那个画面
 * （同一套筛选、同一门选中的语言、时间轴同一格、同一个视图）。
 *
 * 设计取舍：
 *   · 用**明文参数**而不是 base64 一坨 JSON —— URL 里能直接读出筛选条件，
 *     调试和演示时都能指着地址栏说"看，条件在这里"。
 *   · **省略默认值**，所以没做任何操作时 URL 是干净的（不带一堆 `&x=`）。
 *   · 回写用 `history.replaceState`，不往浏览器的前进/后退历史里塞条目
 *     （否则拖一下时间轴就会堆几十条历史，按返回键要按到手软）。
 *   · 应用 URL 时会走 `store.applyIntent`，它本来就有白名单校验
 *     （语系名、特征 ID、等级范围），所以手改坏了的链接不会把界面搞崩。
 */
import { watch, type WatchStopHandle } from 'vue'
import type { useDataset } from '@/stores/dataset'

type Store = ReturnType<typeof useDataset>

/** 把状态编码成查询串（省略默认值） */
export function toQuery(s: Store): string {
  const p = new URLSearchParams()
  if (s.storyStep != null) p.set('s', String(s.storyStep))
  if (s.activeView !== 'map') p.set('v', s.activeView)
  if (s.macroAreas.length) p.set('area', s.macroAreas.join(','))
  if (s.families.length) p.set('fam', s.families.join(','))
  if (s.search.trim()) p.set('q', s.search.trim())
  if (s.featureFilter) {
    p.set('ff', s.featureFilter.value == null
      ? s.featureFilter.featureId
      : `${s.featureFilter.featureId}=${s.featureFilter.value}`)
  }
  if (s.growthMin != null) p.set('gmin', String(s.growthMin))
  if (s.growthMax != null) p.set('gmax', String(s.growthMax))
  if (s.wikiOnly) p.set('wiki', '1')
  if (s.minFeatures != null) p.set('minf', String(s.minFeatures))
  if (s.endangermentLevels.length) p.set('end', s.endangermentLevels.join(','))
  if (s.selected) p.set('sel', s.selected)
  if (s.comparisonSet.length) p.set('cmp', s.comparisonSet.join(','))
  // 默认月份是**最后一个月**（store.load 里会把 monthIndex 推到末尾，默认展示最新数据），
  // 所以判断"是否默认"要跟末位比，而不是跟 0 比 ——
  // 之前写成 `> 0` 导致任何干净状态都会多出一个 m=134。
  const lastMonth = Math.max(s.months.length - 1, 0)
  if (s.monthIndex !== lastMonth) p.set('m', String(s.monthIndex))
  if (s.colorBy !== 'macroarea') p.set('cb', s.colorBy)
  if (s.sizeMode !== 'relative') p.set('sm', s.sizeMode)
  if (!s.showVitality) p.set('voff', '1')
  if (!s.mapDensity) p.set('dots', '1')
  if (s.hideUnselected) p.set('only', '1')
  if (s.lang !== 'zh') p.set('lang', s.lang)
  return p.toString()
}

const VIEWS = ['map', 'growth', 'features', 'matrix', 'endanger']
const SIZES = ['relative', 'absolute']
const COLORS = ['macroarea', 'trend']

/**
 * 从查询串恢复状态。返回是否真的应用了任何参数。
 *
 * ⚠️ 必须在 `store.load()` **之后**调用：applyIntent 要用 familyList / matrix
 * 做白名单校验，数据没到位时会把合法值也当成非法丢掉。
 */
export function applyQuery(s: Store, qs: string): boolean {
  const p = new URLSearchParams(qs)
  if ([...p.keys()].length === 0) return false

  const nums = (k: string): number[] | undefined => {
    const v = p.get(k)
    if (!v) return undefined
    return v.split(',').map(Number).filter((n) => Number.isFinite(n))
  }
  const num = (k: string): number | undefined => {
    const v = p.get(k)
    if (v == null || v === '') return undefined
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }

  // 故事步先走：它会把看板设成那一步的默认状态。
  // 然后下面的显式参数再覆盖上去 —— 这样"在故事某一步上又手动改了筛选"
  // 也能被完整还原（否则 goStory 的默认值会把用户的改动盖掉）。
  const st = num('s')
  if (st != null) s.goStory(st)

  // 筛选类字段交给 applyIntent —— 它已经做了白名单校验
  const ff = p.get('ff')
  s.applyIntent({
    macroAreas: p.get('area')?.split(',').filter(Boolean),
    families: p.get('fam')?.split(',').filter(Boolean),
    nameQuery: p.get('q') ?? undefined,
    featureId: ff ? ff.split('=')[0] : undefined,
    featureValue: ff?.includes('=') ? ff.split('=')[1] : undefined,
    growthMin: num('gmin'),
    growthMax: num('gmax'),
    wikiOnly: p.get('wiki') === '1' ? true : undefined,
    minFeatures: num('minf'),
    endangermentLevels: nums('end'),
  })

  const v = p.get('v')
  if (v && VIEWS.includes(v)) s.activeView = v as Store['activeView']
  if (p.get('sel')) s.selected = p.get('sel')
  if (p.get('cmp')) s.comparisonSet = p.get('cmp')!.split(',').filter(Boolean)
  const m = num('m')
  if (m != null) s.monthIndex = Math.min(Math.max(m, 0), Math.max(s.months.length - 1, 0))
  const cb = p.get('cb')
  if (cb && COLORS.includes(cb)) s.colorBy = cb as Store['colorBy']
  const sm = p.get('sm')
  if (sm && SIZES.includes(sm)) s.sizeMode = sm as Store['sizeMode']
  if (p.get('voff') === '1') s.showVitality = false
  if (p.get('dots') === '1') s.mapDensity = false
  if (p.get('only') === '1') s.hideUnselected = true
  if (p.get('lang') === 'en' || p.get('lang') === 'zh') s.lang = p.get('lang') as 'en' | 'zh'
  return true
}

/**
 * 状态变化时回写 URL。返回停止函数。
 *
 * 节流 250ms：拖时间轴会连续触发，不节流的话每帧都要改一次地址栏。
 */
export function startUrlSync(s: Store): WatchStopHandle {
  let timer: ReturnType<typeof setTimeout> | undefined
  return watch(
    () => toQuery(s),
    (q) => {
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        const url = q ? `${location.pathname}?${q}` : location.pathname
        history.replaceState(null, '', url)
      }, 250)
    },
  )
}

/** 当前页面的完整分享链接 */
export function shareUrl(s: Store): string {
  const q = toQuery(s)
  return `${location.origin}${location.pathname}${q ? `?${q}` : ''}`
}
