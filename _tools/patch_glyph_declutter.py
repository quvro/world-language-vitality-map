"""字形抗拥挤：屏幕空间贪心抽稀。

2,662 个字形在世界视图下必然互相覆盖、糊成一片。
做法：
  1) glyphItems 按"半径 × 不透明度"降序 —— 重要/显眼的先占位
  2) renderGlyph 里维护一个 26px 的屏幕空间哈希，插入前查 3×3 邻域
  3) 与已放置字形重叠（距离 < 半径和 × 0.82）就跳过，返回空 group

因为是**屏幕空间**判断，缩放放大后字距自然拉开，抽稀自动放松 ——
不需要监听 roam，也就不会和漫游动画打架（之前踩过这个坑）。
每轮绘制 ECharts 都从 dataIndex 0 开始，用它来重置占位表。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/components/WorldMap.vue"
s = io.open(P, encoding="utf-8").read()

# ---- 1) 排序：重要的先占位
OLD_RET = "  return out\n})"
NEW_RET = """  // 抗拥挤的前提：重要/显眼的字形先占位（见下方 renderGlyph 的贪心抽稀）
  out.sort((a, b) => (b.r * b.opacity) - (a.r * a.opacity))
  return out
})"""
if OLD_RET in s:
    s = s.replace(OLD_RET, NEW_RET, 1)
    print("  ok   glyphItems 已按重要度排序")
else:
    print("  MISS return out")

# ---- 2) 占位表 + 冲突检测（插在 renderGlyph 之前）
ANCHOR = """/** custom series 的绘制函数。坐标系是 geo，`api.coord` 负责经纬度 → 像素。"""
DECL = """/**
 * 抗拥挤用的屏幕空间占位表。
 *
 * 每个字形以屏幕坐标落格（26px），插入前检查 3×3 邻域里已放置的字形，
 * 只要与其中一个的距离小于两者半径和的 0.82 倍，就认为它放不下。
 * 之所以用屏幕坐标而不是经纬度：缩放后字距会自然拉开，抽稀随之自动放松，
 * 不需要监听 roam，也就避开了"重绘与漫游动画打架"那个老问题。
 */
const GLYPH_CELL = 26
const glyphOcc = new Map<string, { x: number; y: number; r: number }[]>()

function glyphCellKey(x: number, y: number) {
  return `${Math.floor(x / GLYPH_CELL)},${Math.floor(y / GLYPH_CELL)}`
}

function glyphCrowded(x: number, y: number, r: number) {
  const bx = Math.floor(x / GLYPH_CELL)
  const by = Math.floor(y / GLYPH_CELL)
  for (let dx = -1; dx <= 1; dx++) {
    for (let dy = -1; dy <= 1; dy++) {
      const bucket = glyphOcc.get(`${bx + dx},${by + dy}`)
      if (!bucket) continue
      for (const o of bucket) {
        const dist = Math.hypot(o.x - x, o.y - y)
        if (dist < (o.r + r) * 0.82) return true
      }
    }
  }
  return false
}

"""
if ANCHOR in s and "glyphCrowded" not in s:
    s = s.replace(ANCHOR, DECL + ANCHOR, 1)
    print("  ok   已插入占位表与冲突检测")
elif "glyphCrowded" in s:
    print("  ok   已存在，跳过")
else:
    print("  MISS 绘制函数锚点")

# ---- 3) renderGlyph 内部：重置 / 检测 / 登记
OLD_HEAD = """  const x = pt[0]
  const y = pt[1]
  const r = it.r
  const kids: any[] = []"""
NEW_HEAD = """  const x = pt[0]
  const y = pt[1]
  const r = it.r

  // 每轮绘制 ECharts 都从 dataIndex 0 开始 —— 用它重置占位表
  if (params.dataIndex === 0) glyphOcc.clear()
  // 选中的那门永远画出来，否则点一个小语种可能"点了没反应"
  const pinned = store.selected === it.wals_id
  if (!pinned && glyphCrowded(x, y, r)) {
    return { type: 'group', children: [] }
  }
  {
    const key = glyphCellKey(x, y)
    let bucket = glyphOcc.get(key)
    if (!bucket) glyphOcc.set(key, bucket = [])
    bucket.push({ x, y, r })
  }

  const kids: any[] = []"""
if OLD_HEAD in s:
    s = s.replace(OLD_HEAD, NEW_HEAD, 1)
    print("  ok   renderGlyph 已接入抽稀")
else:
    print("  MISS renderGlyph 头部")

io.open(P, "w", encoding="utf-8").write(s)
