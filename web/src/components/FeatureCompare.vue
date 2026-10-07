<script setup lang="ts">
/**
 * 条件对比工作台 —— 签名交互之二。
 *
 * 想回答的问题：**语言的结构特征，和它在数字空间的处境有关系吗？**
 * 选一个语法特征（如语序 SOV / SVO / VSO），把它拆成若干组，比较各组：
 *   · 数字在场率 —— 这一组里有多大比例的语言拥有维基百科版本
 *   · 十年趋势   —— 这一组里有维基版本的语言，增长中位数与四分位区间
 *
 * 两处刻意的设计：
 *   1. 左侧覆盖率条形图**同时充当特征选择器** —— 哪些特征数据够做对比，一眼可见，
 *      点一下即可切换对比目标。可视化即控件。
 *   2. 分组统计走 store.filteredBase（不含特征筛选），否则点选一个分组后
 *      其它分组会消失、对比图自己塌掉。
 *
 * 全部用 CSS 绘制，不引图表库 —— 签名交互要看起来是原创的。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'
import { semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const C = semanticColors()

/** 一个分组至少要有这么多门语言才参与对比，否则是噪声 */
const MIN_GROUP = 12

/**
 * 每个特征的两个指标，一起算：
 *   n      覆盖率 —— 有多少门语言被 WALS 收录了该特征
 *   spread 分组差异 —— 各组「数字在场率」的极差
 *
 * 覆盖率决定数据够不够做对比，分组差异决定**值不值得**做对比。
 * 实测语序特征只有 4 个百分点的差异，而 Relativization on Subjects 有 83 个 ——
 * 只看覆盖率会挑到一个无聊的特征。所以按分组差异排序。
 */
const coverage = computed(() => {
  const m = store.matrix
  if (!m) return []
  const base = store.filteredBase
  const keep = new Set(base.map((l) => l.wals_id))
  const hasWiki = new Map(base.map((l) => [l.wals_id, !!l.wiki_code]))
  const keys: string[] = []
  const pos: number[] = []
  m.language_keys.forEach((k, i) => {
    if (keep.has(k)) { keys.push(k); pos.push(i) }
  })
  const names = new Map(store.features?.features.map((f) => [f.ID, f.Name]) ?? [])

  return m.feature_ids.map((fid, fi) => {
    const row = m.values[fi]
    let n = 0
    const acc = new Map<string, { t: number; w: number }>()
    for (let j = 0; j < pos.length; j++) {
      const v = row[pos[j]]
      if (v == null) continue
      n++
      let a = acc.get(v)
      if (!a) { a = { t: 0, w: 0 }; acc.set(v, a) }
      a.t++
      if (hasWiki.get(keys[j])) a.w++
    }
    const rates: number[] = []
    for (const a of acc.values()) if (a.t >= MIN_GROUP) rates.push(a.w / a.t)
    const spread = rates.length < 2 ? 0 : Math.max(...rates) - Math.min(...rates)
    return { fid, name: names.get(fid) || fid, n, spread, groups: rates.length }
  }).sort((a, b) => b.spread - a.spread || b.n - a.n)
})

const topCoverage = computed(() => coverage.value.slice(0, 16))
const maxCoverage = computed(() => Math.max(...coverage.value.map((c) => c.n), 1))
const maxSpread = computed(() => Math.max(...coverage.value.map((c) => c.spread), 0.01))

const featureName = computed(() => {
  const fid = store.compareFeature
  return store.features?.features.find((f) => f.ID === fid)?.Name ?? '—'
})

interface Group {
  value: string
  label: string
  total: number
  withWiki: number
  wikiRate: number
  median: number | null
  q1: number | null
  q3: number | null
}

const groups = computed<Group[]>(() => {
  const fid = store.compareFeature
  const m = store.matrix
  if (!fid || !m) return []
  const fi = m.feature_ids.indexOf(fid)
  if (fi < 0) return []
  const row = m.values[fi]
  const labels = store.codeLabel

  const acc = new Map<string, { total: number; wiki: number; g: number[] }>()
  for (const l of store.filteredBase) {
    const i = store.keyIndex[l.wals_id]
    if (i == null) continue
    const v = row[i]
    if (v == null) continue
    let a = acc.get(v)
    if (!a) { a = { total: 0, wiki: 0, g: [] }; acc.set(v, a) }
    a.total++
    if (l.wiki_code) a.wiki++
    if (l.baseline_ok && l.growth != null) a.g.push(l.growth * 100)
  }

  const out: Group[] = []
  for (const [value, a] of acc) {
    if (a.total < MIN_GROUP) continue
    const g = a.g.slice().sort((x, y) => x - y)
    const q = (p: number) => (g.length ? g[Math.min(g.length - 1, Math.floor(g.length * p))] : null)
    out.push({
      value,
      label: labels.get(`${fid}\u0000${value}`) || `${value}`,
      total: a.total,
      withWiki: a.wiki,
      wikiRate: a.wiki / a.total,
      median: g.length ? q(0.5) : null,
      q1: g.length ? q(0.25) : null,
      q3: g.length ? q(0.75) : null,
    })
  }
  return out.sort((a, b) => b.wikiRate - a.wikiRate)
})

const activeFilter = computed(() => store.featureFilter)

/** 趋势轴：裁剪到 [-100, +300]，超出的用箭头提示，避免被极端值压平 */
const AX_MIN = -100
const AX_MAX = 300
const clamp = (v: number) => Math.min(Math.max(v, AX_MIN), AX_MAX)
const pos = (v: number) => ((clamp(v) - AX_MIN) / (AX_MAX - AX_MIN)) * 100

const overall = computed(() => {
  const base = store.filteredBase
  const withWiki = base.filter((l) => l.wiki_code).length
  return { total: base.length, withWiki, rate: base.length ? withWiki / base.length : 0 }
})
</script>

<template>
  <section class="wb">
    <header>
      <div>
        <h2>条件对比</h2>
        <p class="hint">
          选一个语法特征，看不同取值的语言在数字空间的处境差异
        </p>
      </div>
      <label class="picker">
        <span>特征</span>
        <select :value="store.compareFeature ?? ''"
                @change="store.setCompareFeature(($event.target as HTMLSelectElement).value)">
          <option v-for="c in coverage.slice(0, 80)" :key="c.fid" :value="c.fid">
            {{ c.name }}（{{ c.n.toLocaleString('en-US') }}）
          </option>
        </select>
      </label>
    </header>

    <div class="body">
      <!-- 左：特征选择器。同时给出覆盖率与分组差异，才知道哪个特征值得看 -->
      <div class="cov">
        <h3>选一个特征 <span class="n">按分组差异排序 · 点选切换</span></h3>
        <div class="colhead">
          <span>特征</span><span>覆盖率</span><span>语言</span><span>分组差异</span>
        </div>
        <ul>
          <li v-for="c in topCoverage" :key="c.fid">
            <button
              :class="{ on: store.compareFeature === c.fid }"
              :title="`${c.name}\n覆盖 ${c.n} 门语言，${c.groups} 个分组，在场率极差 ${(c.spread * 100).toFixed(0)} 个百分点`"
              @click="store.setCompareFeature(c.fid)"
            >
              <span class="nm">{{ c.name }}</span>
              <span class="track"><i :style="{ width: (c.n / maxCoverage) * 100 + '%' }" /></span>
              <span class="ct num">{{ c.n.toLocaleString('en-US') }}</span>
              <span class="sp num" :style="{ opacity: 0.35 + 0.65 * (c.spread / maxSpread) }">
                {{ (c.spread * 100).toFixed(0) }}
              </span>
            </button>
          </li>
        </ul>
        <p class="foot">
          <strong>覆盖率</strong>决定数据够不够做对比；<strong>分组差异</strong>（各组数字在场率的极差，
          单位百分点）决定<strong>值不值得</strong>做对比。语序这类常识特征差异往往只有几个百分点，
          而差异最大的特征可达 80 以上。低于 {{ MIN_GROUP }} 门语言的分组不参与统计。
        </p>
      </div>

      <!-- 右：分组对比 -->
      <div class="cmp">
        <h3>
          {{ featureName }}
          <span class="n">{{ groups.length }} 个分组 · 整体在场率
            {{ (overall.rate * 100).toFixed(1) }}%</span>
        </h3>

        <div v-if="!groups.length" class="empty">
          当前筛选下没有足够大的分组。放宽左侧筛选，或换一个覆盖率更高的特征。
        </div>

        <ul v-else class="rows">
          <li
            v-for="g in groups" :key="g.value"
            :class="{ on: activeFilter?.featureId === store.compareFeature && activeFilter?.value === g.value }"
          >
            <button @click="store.toggleFeatureFilter(store.compareFeature!, g.value)">
              <span class="lb">
                <span class="t">{{ g.label }}</span>
                <span class="c num">{{ g.total }} 门</span>
              </span>

              <span class="rate">
                <span class="bar">
                  <i :style="{ width: (g.wikiRate * 100) + '%' }" />
                  <em class="ref" :style="{ left: (overall.rate * 100) + '%' }"
                      :title="`整体在场率 ${(overall.rate * 100).toFixed(1)}%`" />
                </span>
                <span class="v num">{{ (g.wikiRate * 100).toFixed(0) }}%</span>
              </span>

              <span class="trend">
                <template v-if="g.median != null">
                  <span class="axis">
                    <i class="zero" :style="{ left: pos(0) + '%' }" />
                    <i class="band"
                       :style="{ left: pos(g.q1!) + '%', width: Math.max(pos(g.q3!) - pos(g.q1!), 1) + '%' }" />
                    <i class="med" :style="{ left: pos(g.median) + '%' }" />
                  </span>
                  <span class="mv num" :class="g.median >= 0 ? 'up' : 'down'">
                    {{ g.median >= 0 ? '+' : '' }}{{ g.median.toFixed(0) }}%
                  </span>
                </template>
                <span v-else class="mv none">样本不足</span>
              </span>
            </button>
          </li>
        </ul>

        <div class="lgd">
          <span><i class="sw rate" />数字在场率（该组有维基版本的比例，竖线为整体水平）</span>
          <span><i class="sw med" />十年增长中位数</span>
          <span><i class="sw band" />四分位区间（趋势轴裁剪到 −100% ~ +300%）</span>
          <span v-if="activeFilter" class="clear">
            已筛选：<strong>{{ activeFilter.value }}</strong>
            <button @click="store.featureFilter = null">取消</button>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.wb {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--sp-4); display: flex; flex-direction: column;
  min-height: 0; height: 100%;
}
header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: var(--sp-4); margin-bottom: var(--sp-3); flex: none;
}
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 0; font-size: var(--fs-small); color: var(--text-muted); }

.picker { display: flex; align-items: center; gap: var(--sp-2); font-size: var(--fs-small); color: var(--text-secondary); }
.picker select {
  max-width: 260px; padding: 5px 9px; font-family: inherit; font-size: var(--fs-small);
  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-canvas); color: var(--text-primary);
}

.body {
  flex: 1; min-height: 0;
  display: grid; grid-template-columns: 300px minmax(0, 1fr);
  gap: var(--sp-5);
}
@media (max-width: 1100px) {
  .body { grid-template-columns: 1fr; }
  .cov { max-height: 220px; }
}

h3 {
  margin: 0 0 var(--sp-2); font-size: var(--fs-micro);
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-muted); font-weight: 600;
}
h3 .n { text-transform: none; letter-spacing: 0; font-weight: 400; margin-left: 6px; }

/* ------------------------------------------------------------ 覆盖率列 */
.cov { display: flex; flex-direction: column; min-height: 0; }
.colhead {
  display: grid; grid-template-columns: 1fr 52px 40px 44px;
  gap: var(--sp-2); padding: 0 6px var(--sp-1);
  font-size: var(--fs-micro); color: var(--text-muted);
}
.colhead span:not(:first-child) { text-align: right; }
.cov ul { list-style: none; margin: 0; padding: 0; overflow: auto; flex: 1; min-height: 0; }
.cov button {
  display: grid; grid-template-columns: 1fr 52px 40px 44px;
  align-items: center; gap: var(--sp-2);
  width: 100%; border: 0; background: transparent; cursor: pointer;
  padding: 3px 6px; border-radius: var(--radius-sm);
  font-family: inherit; font-size: var(--fs-small); color: var(--text-secondary);
  text-align: left;
}
.cov button:hover { background: var(--bg-subtle); }
.cov button.on { background: var(--accent-soft); color: var(--accent); font-weight: 500; }
.cov .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cov .track { height: 5px; background: var(--bg-subtle); border-radius: var(--radius-pill); overflow: hidden; }
.cov .track i { display: block; height: 100%; background: currentColor; opacity: 0.55; border-radius: var(--radius-pill); }
.cov .ct { text-align: right; font-size: var(--fs-micro); color: var(--text-muted); }
.cov .sp {
  text-align: right; font-size: var(--fs-micro); font-weight: 600;
  color: var(--accent);
}
.foot {
  margin: var(--sp-2) 0 0; padding-top: var(--sp-2);
  border-top: 1px solid var(--border);
  font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.7;
}

/* ------------------------------------------------------------ 对比列 */
.cmp { display: flex; flex-direction: column; min-height: 0; }
.rows { list-style: none; margin: 0; padding: 0; overflow: auto; flex: 1; min-height: 0; }
.rows li { border-bottom: 1px solid var(--border); }
.rows li.on { background: var(--accent-soft); }
.rows button {
  display: grid;
  grid-template-columns: 168px minmax(140px, 1fr) 220px;
  align-items: center; gap: var(--sp-4);
  width: 100%; border: 0; background: transparent; cursor: pointer;
  padding: 7px 8px; font-family: inherit; text-align: left;
  transition: background var(--dur-fast) var(--ease-out);
}
.rows button:hover { background: var(--bg-subtle); }

.lb { display: flex; flex-direction: column; }
.lb .t { font-size: var(--fs-small); color: var(--text-primary); font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lb .c { font-size: var(--fs-micro); color: var(--text-muted); }

.rate { display: flex; align-items: center; gap: var(--sp-2); }
.rate .bar {
  position: relative; flex: 1; height: 9px;
  background: var(--bg-subtle); border-radius: var(--radius-pill); overflow: hidden;
}
.rate .bar i { display: block; height: 100%; background: var(--positive); opacity: 0.8; border-radius: var(--radius-pill); }
.rate .bar .ref {
  position: absolute; top: -2px; bottom: -2px; width: 1.5px;
  background: var(--text-primary); opacity: 0.55;
}
.rate .v { font-size: var(--fs-small); color: var(--text-secondary); width: 34px; text-align: right; }

.trend { display: flex; align-items: center; gap: var(--sp-2); }
.trend .axis { position: relative; flex: 1; height: 12px; }
.trend .zero { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--border-strong); }
.trend .band {
  position: absolute; top: 3px; height: 6px;
  background: var(--accent); opacity: 0.22; border-radius: var(--radius-pill);
}
.trend .med {
  position: absolute; top: 0; bottom: 0; width: 2px;
  background: var(--accent); border-radius: 1px;
}
.mv { font-size: var(--fs-small); width: 52px; text-align: right; }
.mv.up { color: var(--positive); }
.mv.down { color: var(--negative); }
.mv.none { color: var(--text-muted); font-size: var(--fs-micro); }

.empty { padding: var(--sp-5); text-align: center; color: var(--text-muted); font-size: var(--fs-small); line-height: 1.7; }

.lgd {
  display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-4);
  padding-top: var(--sp-2); margin-top: var(--sp-2);
  border-top: 1px solid var(--border);
  font-size: var(--fs-micro); color: var(--text-muted);
}
.lgd span { display: inline-flex; align-items: center; gap: 5px; }
.lgd .sw { width: 12px; height: 6px; border-radius: 2px; flex: none; }
.lgd .sw.rate { background: var(--positive); opacity: 0.8; }
.lgd .sw.med { width: 2px; height: 10px; background: var(--accent); border-radius: 1px; }
.lgd .sw.band { background: var(--accent); opacity: 0.22; }
.lgd .clear { margin-left: auto; color: var(--text-secondary); }
.lgd .clear strong { color: var(--accent); }
.lgd .clear button {
  border: 0; background: transparent; color: var(--accent); cursor: pointer;
  font-family: inherit; font-size: inherit; text-decoration: underline;
}
</style>
