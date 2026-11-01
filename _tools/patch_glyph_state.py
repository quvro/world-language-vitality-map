"""加入「复合字形」：一个语言一个 glyph，多个维度映射到字形的不同部件。

思路借自 GlottoVis —— 用字形的不同部位分别编码不同维度，而不是一个点只编码一个变量。
配套一组开关，让用户可以逐维度打开/关闭，直观看到"这个维度被关掉之后，地图还剩多少信息"。

改动：
  · store：mapDensity(boolean) → mapMode('density'|'dots'|'glyph')；
           新增 glyphChannels 五个通道开关
  · urlState：mm=density|dots|glyph（兼容旧的 dots=1）
  · WorldMap：glyph 计算 + custom series 绘制 + 图例三态 + 浮动开关面板
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def patch(path, pairs, label):
    s = io.open(path, encoding="utf-8").read()
    hit = 0
    for old, new in pairs:
        if old in s:
            s = s.replace(old, new, 1)
            hit += 1
        else:
            print(f"  [{label}] 未匹配：{old.splitlines()[0][:56]}")
    io.open(path, "w", encoding="utf-8").write(s)
    print(f"  [{label}] 替换 {hit}/{len(pairs)}")


# ---------------------------------------------------------------- store
patch("web/src/stores/dataset.ts", [
    (
        '''  /**
   * 地图底图的渲染方式：密度块 / 逐点。
   *
   * **刻意做成用户显式切换，而不是跟随缩放自动切换。**
   * 自动切换需要在漫游过程中 setOption，那会打断 geo 的缩放补间，
   * 让渲染出的地图与模型里的 zoom/center 不一致（表现为"缩放时地图错位，
   * 点一下又复位"）。去掉这条路径后，缩放期间不再发生任何 setOption。
   */
  mapDensity: boolean''',
        '''  /**
   * 地图底图的渲染方式：密度块 / 逐点 / **复合字形**。
   *
   * **刻意做成用户显式切换，而不是跟随缩放自动切换。**
   * 自动切换需要在漫游过程中 setOption，那会打断 geo 的缩放补间，
   * 让渲染出的地图与模型里的 zoom/center 不一致（表现为"缩放时地图错位，
   * 点一下又复位"）。去掉这条路径后，缩放期间不再发生任何 setOption。
   *
   * `glyph` 模式下每个语言被画成一个由若干部件组成的小符号，
   * 各部件编码哪个维度由 `glyphChannels` 决定。
   */
  mapMode: 'density' | 'dots' | 'glyph'
  /**
   * 字形各通道的开关。关掉的通道用中性色画（而不是不画），
   * 这样"关掉这个维度"看得见代价：地图会立刻变灰一片。
   */
  glyphChannels: {
    /** 外环颜色 ← 濒危等级 */
    ring: boolean
    /** 环内扇形 ← 描写深度（0–5） */
    arc: boolean
    /** 中心点 ← 是否有维基百科版本 */
    core: boolean
    /** 字形大小 ← 当月浏览量 */
    size: boolean
    /** 外围刻度 ← 维基百科之外的项目数 */
    ticks: boolean
  }''',
    ),
    ("    mapDensity: true,",
     "    mapMode: 'density',\n"
     "    glyphChannels: { ring: true, arc: true, core: true, size: true, ticks: true },"),
], "store")

# ---------------------------------------------------------------- urlState
patch("web/src/urlState.ts", [
    ("  if (!s.mapDensity) p.set('dots', '1')",
     "  if (s.mapMode !== 'density') p.set('mm', s.mapMode)\n"
     "  const gc = s.glyphChannels\n"
     "  const gcBits = [gc.ring, gc.arc, gc.core, gc.size, gc.ticks]\n"
     "    .map((v) => (v ? '1' : '0')).join('')\n"
     "  if (gcBits !== '11111') p.set('gc', gcBits)"),
    ("  if (p.get('dots') === '1') s.mapDensity = false",
     "  const mm = p.get('mm')\n"
     "  if (mm === 'dots' || mm === 'glyph' || mm === 'density') s.mapMode = mm\n"
     "  // 兼容旧链接：早期的 dots=1 表示\"逐点\"\n"
     "  else if (p.get('dots') === '1') s.mapMode = 'dots'\n"
     "  const gc = p.get('gc')\n"
     "  if (gc && /^[01]{5}$/.test(gc)) {\n"
     "    s.glyphChannels = {\n"
     "      ring: gc[0] === '1', arc: gc[1] === '1', core: gc[2] === '1',\n"
     "      size: gc[3] === '1', ticks: gc[4] === '1',\n"
     "    }\n"
     "  }"),
], "urlState")

# ---------------------------------------------------------------- verify
patch("web/preview/verify-map-repaint.mjs", [
    ("  /store\\.mapDensity/.test(src) && !/AGG_ZOOM/.test(src))",
     "  /store\\.mapMode/.test(src) && !/AGG_ZOOM/.test(src))"),
    ("  && /store\\.mapDensity = false/.test(src))",
     "  && /store\\.mapMode = 'dots'/.test(src))"),
    ("  /setOption\\(\\{ geo: \\{ center: \\[lng, lat\\], zoom: 6 \\} \\}\\)[\\s\\S]{0,120}store\\.mapDensity = false/.test(src))",
     "  /setOption\\(\\{ geo: \\{ center: \\[lng, lat\\], zoom: 6 \\} \\}\\)[\\s\\S]{0,120}store\\.mapMode = 'dots'/.test(src))"),
], "verify")
