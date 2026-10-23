/**
 * 验证凸包 —— 「选中语言所属语系」的外轮廓靠它。
 *
 * 为什么值得单独测：凸包算错在图上**看不出来**。轮廓依然会是一个像模像样的多边形，
 * 只是可能少了几个点、或者把内点当成顶点。所以用几组构造用例逐项断言。
 */
import { createHarness } from './_harness.mjs'

let fail = 0
const check = (label, cond, extra = '') => {
  if (!cond) fail++
  console.log(`  ${cond ? 'OK  ' : 'FAIL'} ${label}${extra ? '  → ' + extra : ''}`)
}

const h = await createHarness()
try {
  const { convexHull, spansDateline, DATELINE_SPAN } = await h.load('hull.ts')

  console.log('=== 1. 基本形状 ===')
  // 正方形 + 一个内点：凸包应恰好是 4 个顶点，内点必须被排除
  const sq = [[0, 0], [10, 0], [10, 10], [0, 10], [5, 5]]
  const hull = convexHull(sq)
  check('正方形 + 内点 → 凸包 4 个顶点', hull.length === 4, `${hull.length}`)
  check('内点 (5,5) 不在凸包上',
    !hull.some((p) => p[0] === 5 && p[1] === 5))
  check('四个角都在凸包上',
    [[0, 0], [10, 0], [10, 10], [0, 10]].every(
      (c) => hull.some((p) => p[0] === c[0] && p[1] === c[1])))

  console.log('\n=== 2. 退化输入 ===')
  check('0 个点 → 空', convexHull([]).length === 0)
  check('1 个点 → 原样返回', convexHull([[3, 4]]).length === 1)
  check('2 个点 → 原样返回（画不出多边形，调用方要跳过）',
    convexHull([[0, 0], [1, 1]]).length === 2)
  // 共线：monotone chain 的 pop 条件是 <= 0，会把中间点全弹掉 → 只剩两端
  const col = [[0, 0], [1, 1], [2, 2], [3, 3]]
  check('共线 → 退化成两端点（不会返回一个假多边形）',
    convexHull(col).length === 2, `${convexHull(col).length}`)
  check('重复点不会让凸包爆炸',
    convexHull([[1, 1], [1, 1], [1, 1], [2, 2], [0, 0]]).length >= 2)

  console.log('\n=== 3. 顺序无关（凸包是几何性质，不该依赖输入顺序）===')
  const pts = [[0, 0], [4, 0], [4, 4], [2, 7], [0, 4], [2, 2]]
  const a = convexHull(pts).map((p) => p.join(',')).sort().join('|')
  const b = convexHull([...pts].reverse()).map((p) => p.join(',')).sort().join('|')
  const c = convexHull([pts[2], pts[5], pts[0], pts[4], pts[1], pts[3]])
    .map((p) => p.join(',')).sort().join('|')
  check('三种输入顺序得到同一组顶点', a === b && b === c)

  console.log('\n=== 4. 跨 180° 经线检测 ===')
  check('正常范围不算跨界', !spansDateline([[10, 0], [120, 0], [130, 0]]))
  // 南岛语系：从马达加斯加(~47E)到复活节岛(~109W=-109) —— 跨度 156，不算跨界
  check('南岛语系实际跨度 156° → 不作弊跳掉',
    !spansDateline([[47, -20], [-109, -27], [170, -45]]),
    `span=${300} 阈值`)
  // 真正跨界的例子：经度从 -170 到 +170，跨度 340
  check('跨太平洋（-170 与 +170 同现）判为跨界',
    spansDateline([[-170, 0], [170, 0], [0, 0]]))
  check('阈值本身可被引用', DATELINE_SPAN === 300)

  console.log('\n=== 5. 用真实语系数据跑一遍 ===')
  const s = await h.freshStore()
  const famAll = s.familyList
  const trials = famAll.slice(0, 8)
  for (const f of trials) {
    const rows = s.langs.filter(
      (l) => l.family === f.family && l.latitude && l.longitude)
    const p = rows.map((l) => [Number(l.longitude), Number(l.latitude)])
    const hh = convexHull(p)
    const skipped = spansDateline(p)
    const ok = p.length < 3
      ? hh.length === p.length
      : (skipped || hh.length >= 3)
    if (!ok) fail++
    console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${f.family.padEnd(22)}`
      + ` ${String(rows.length).padStart(4)} 门  凸包顶点 ${String(hh.length).padStart(3)}`
      + (skipped ? '  （跨 180°，跳过轮廓）' : ''))
  }
} finally {
  h.cleanup()
}

console.log(`\n${fail === 0 ? '全部通过' : fail + ' 项失败'}`)
process.exit(fail === 0 ? 0 : 1)
