/**
 * 凸包（Andrew monotone chain）—— 给地图上「选中语言所属语系」画外轮廓用。
 *
 * 单独抽出来的原因：凸包算错在图上很难看出来（轮廓依然是个像模像样的多边形，
 * 只是漏了某几个点），所以必须能被单独测试。见 verify-hull.mjs。
 *
 * 两个已知的坑，都做了处理：
 *   1. **退化输入**：点数 < 3、或者所有点共线时，凸包会退化成一条线甚至空集。
 *      共线时 monotone chain 的 pop 条件（`<= 0`）会把中间点全弹掉，
 *      结果只剩两个端点 —— 对画轮廓来说这是对的（两点画不出多边形）。
 *   2. **跨 180° 经线**：南岛语系这类横跨太平洋的语系，经度从 -170 到 +170，
 *      直接用经度算凸包会得到一个横跨整个地图的巨大多边形，看起来像幻觉。
 *      所以调用方应先过 `spansDateline()`，为真就跳过轮廓。
 */

export type P = [number, number]

/** 经度跨度超过这个值就认为跨了 180° 经线（不用 300 是因为太平洋语系很常见） */
export const DATELINE_SPAN = 300

export function spansDateline(pts: P[]): boolean {
  if (pts.length < 2) return false
  let lo = Infinity
  let hi = -Infinity
  for (const [x] of pts) {
    if (x < lo) lo = x
    if (x > hi) hi = x
  }
  return hi - lo > DATELINE_SPAN
}

export function convexHull(pts: P[]): P[] {
  if (pts.length < 3) return [...pts]
  const p = [...pts].sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const cross = (o: P, a: P, b: P) =>
    (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const lower: P[] = []
  for (const q of p) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop()
    lower.push(q)
  }
  const upper: P[] = []
  for (let i = p.length - 1; i >= 0; i--) {
    const q = p[i]
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop()
    upper.push(q)
  }
  lower.pop()
  upper.pop()
  return lower.concat(upper)
}
