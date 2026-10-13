<script setup lang="ts">
/**
 * 濒危 × 关注：现实濒危程度不同的语言，在数字世界获得的关注是否有差异。
 *
 * 数据用**统一濒危等级**（AES 优先、UNESCO 补缺，覆盖 98.2%）——
 * 不能用 UNESCO 单独做：它只收濒危语言，没有"未濒危"档，散点图会严重偏斜。
 *
 * ⚠️ 这个视图有一个**必须处理的表现陷阱**：
 * 散点图只能画出**有维基版本**的语言（269 门），另外 2,393 门根本没有点可画。
 * 只看散点会得出「濒危语言阅读量也不低」的错误印象。
 * 所以散点图下方配了一条「缺席」条，把"有多少根本没出现在图里"直接显示出来。
 *
 * 三个结论：
 *   1. 存在性随濒危程度急剧下降（未濒危 18.0% → 已灭绝 0.9%）
 *   2. 但最大的一群是**语言学上未濒危、却在数字世界完全缺席**的 792 门语言
 *      （非洲 382、巴布亚 214），不是濒危语言
 *   3. 少数**已灭绝**的语言在数字空间反而"复活"了且高速增长
 *      （康沃尔语、马恩岛语）—— 语言复兴运动的数字痕迹
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { endangermentScale, semanticColors } from '@/theme/echarts-theme.js'
import { useChartResize } from '@/useChartResize'

const store = useDataset()
const { language: langLabel, macro: macroLabel } = useDisplayNames()
const RAMP = endangermentScale()
const C = semanticColors()
const e = () => (window as any).echarts

const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)

const T = {
  zh: {
    title: '濒危 × 关注',
    sub: '现实濒危程度不同的语言，在数字世界获得的关注有差异吗？',
    scatter: '① 濒危等级 × 维基百科月阅读量',
    scatterSub: '纵轴对数刻度 · 只有拥有维基版本的语言才画得出来',
    absence: '② 但绝大多数语言根本不在上图里',
    absenceSub: '这是本视图最重要的一块 —— 别只看散点',
    absenceLegend: '有维基版本 / 无维基版本',
    watch: '③ 值得进一步关注的语言',
    watchSub: '点一行在全局选中该语言',
    catA: '已灭绝，却仍有维基版本且高速增长',
    catASub: '语言复兴运动的数字痕迹 —— 口语层面已灭绝，数字空间反而在增长',
    catB: '垂危，但有维基版本',
    catBSub: '关注度不低，说明还有社群在维护',
    catC: '语言学上未濒危，却完全没有维基版本',
    catCSub: (n: string, other: string, geo: string) =>
      `缺席数量最多的**单一等级**（${n} 门）；五个濒危档合计缺席 ${other} 门。` +
      `它们不需要抢救，在数字世界却没有位置 —— ${geo}`,
    catD: '濒危且增长最快',
    catDSub: '数字关注度正在快速上升的濒危语言',
    level: '等级', langs: '语言', wiki: '有维基', none: '无',
    views: '月阅读量', growth: '十年变化', more: (n: string) => `另有 ${n} 门`,
    caveat: '口径与陷阱',
    caveat1: (a: string, b: string, c: string) => `濒危等级优先用 Glottolog AES（覆盖 ${a} 门），其余用 UNESCO 补缺（${b} 门），共漏 ${c} 门。两者 6 级一一对应。`,
    caveat2: 'UNESCO 名录只收濒危语言（2,593 条里仅 82 条 safe），所以绝不能只用它 —— 那会看不到"未濒危"这一档。',
    caveat3: '「阅读量」是维基百科版本的浏览量，不等于使用者人数，也不等于语言活力。它系统性偏向有文字传统、有网络接入的语言。',
    caveat4: '无维基版本 ≠ 该语言没人用。维基百科的开设需要社群推动与审批，是一项高门槛的组织行为。',
    empty: '未跑 pipeline/06_fetch_aes.py，没有濒危等级数据。',
  },
  en: {
    title: 'Endangerment × attention',
    sub: 'Do languages at different levels of endangerment get different digital attention?',
    scatter: '① Endangerment level × monthly Wikipedia pageviews',
    scatterSub: 'log scale · only languages that have a Wikipedia can be plotted',
    absence: '② But most languages are not in the chart above at all',
    absenceSub: 'the most important panel here — do not read the scatter alone',
    absenceLegend: 'has Wikipedia / no Wikipedia',
    watch: '③ Languages worth a closer look',
    watchSub: 'click a row to select it globally',
    catA: 'Extinct, yet has a Wikipedia that is growing fast',
    catASub: 'digital traces of language revival — dead as a vernacular, alive online',
    catB: 'Moribund, but has a Wikipedia',
    catBSub: 'noticeable readership means a community is still maintaining it',
    catC: 'Not endangered linguistically, yet no Wikipedia at all',
    catCSub: (n: string, other: string, geo: string) =>
      `The largest **single** band by number of absences (${n}); the five endangered bands together account for ${other}. ` +
      `They need no rescue, yet have no place online — ${geo}`,
    catD: 'Endangered and fastest growing',
    catDSub: 'endangered languages whose digital attention is rising quickly',
    level: 'Level', langs: 'Langs', wiki: 'w/ wiki', none: 'none',
    views: 'views/mo', growth: '10-yr', more: (n: string) => `+${n} more`,
    caveat: 'Scope and pitfalls',
    caveat1: (a: string, b: string, c: string) => `Endangerment uses Glottolog AES first (${a} languages), UNESCO as fallback (${b}), ${c} uncovered. The two 6-level scales correspond 1:1.`,
    caveat2: 'The UNESCO Atlas only lists endangered languages (only 82 of 2,593 are “safe”), so it cannot be used alone — the “not endangered” band would be invisible.',
    caveat3: '“Views” means Wikipedia pageviews, not speaker numbers and not language vitality. It is systematically biased towards languages with a written tradition and online population.',
    caveat4: 'No Wikipedia edition ≠ nobody uses the language. Creating one requires community effort and an approval process — a high organisational bar.',
    empty: 'pipeline/06_fetch_aes.py has not been run — no endangerment data.',
  },
} as const
const t = computed(() => T[store.lang])

const ebw = computed(() => store.endangermentByWals)
const HAS_DATA = computed(() => !!(store.aes || store.endangerment))

const LEVEL_LABEL = (lv: number): string => {
  const l = store.aes?.levels?.[String(lv)] ?? store.endangerment?.levels?.[String(lv)]
  if (!l) return String(lv)
  return store.lang === 'zh' ? (l.zh ?? l.en) : l.en
}

const fmt = (n: number) => n.toLocaleString('en-US')
const pct = (r: number) => `${(r * 100).toFixed(1)}%`
/** 确定性抖动：同一个语言每次渲染位置一致，否则刷新会乱跳 */
function jitter(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return ((h & 0xffff) / 0xffff - 0.5) * 0.56
}

/** ① 散点：只有有维基版本、且能取到阅读量的语言 */
const dots = computed(() => {
  const ramp = RAMP
  return store.langs
    .filter((l) => l.wiki_code && (l.views_recent ?? 0) > 0 && ebw.value[l.wals_id])
    .map((l) => {
      const lv = ebw.value[l.wals_id]
      return {
        name: langLabel(l),
        wals_id: l.wals_id,
        value: [lv + jitter(l.wals_id), l.views_recent, lv],
        symbolSize: Math.max(6, Math.min(26, 5 + Math.sqrt(l.views_recent!) / 700)),
        itemStyle: { color: ramp[lv - 1], opacity: 0.82 },
        growth: l.growth,
        baseline_ok: l.baseline_ok,
      }
    })
})

/** 需要直接标出名字的点 */
const NOTABLE = ['kw', 'gv', 'trv', 'haw', 'vep', 'lld', 'ga']
const notableSet = computed(() => new Set(NOTABLE))

/** ② 每一级的缺席情况 */
const absence = computed(() =>
  [1, 2, 3, 4, 5, 6].map((lv) => {
    const rows = store.langs.filter((l) => ebw.value[l.wals_id] === lv)
    const wiki = rows.filter((l) => l.wiki_code).length
    return {
      lv, label: LEVEL_LABEL(lv), color: RAMP[lv - 1],
      n: rows.length, wiki, none: rows.length - wiki,
      rate: rows.length ? wiki / rows.length : 0,
    }
  }).filter((d) => d.n > 0)
)

/** ③ 值得关注的语言 */
const worth = computed(() => {
  const rows = store.langs.filter((l) => ebw.value[l.wals_id])
  const byViews = (a: any, b: any) => (b.views_recent ?? 0) - (a.views_recent ?? 0)
  const byGrowth = (a: any, b: any) => (b.growth ?? -9) - (a.growth ?? -9)
  const hasWiki = (l: any) => !!l.wiki_code
  const catC = rows.filter((l) => ebw.value[l.wals_id] === 1 && !hasWiki(l))
    .sort((a, b) => (store.featureCount[b.wals_id] ?? 0) - (store.featureCount[a.wals_id] ?? 0))
  // 五个濒危档的缺席合计 —— 用来把「单一等级最多」和「合计更多」两件事说清楚
  const otherMissing = rows.filter((l) => ebw.value[l.wals_id] >= 2 && !hasWiki(l)).length
  // 缺席的地理分布：这是"数字基础设施不平等"的直接证据
  const geo = new Map<string, number>()
  for (const l of catC) {
    const k = l.macroarea || '—'
    geo.set(k, (geo.get(k) ?? 0) + 1)
  }
  const geoText = [...geo.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2)
    .map(([k, v]) => `${store.lang === 'zh' ? macroLabel(k) : k} ${v}`).join('、')
  return [
    {
      key: 'A', title: t.value.catA, sub: t.value.catASub,
      rows: rows.filter((l) => ebw.value[l.wals_id] >= 5 && hasWiki(l)).sort(byViews),
    },
    {
      key: 'B', title: t.value.catB, sub: t.value.catBSub,
      rows: rows.filter((l) => ebw.value[l.wals_id] === 4 && hasWiki(l)).sort(byViews),
    },
    {
      key: 'C', title: t.value.catC,
      sub: (t.value.catCSub as (a: string, b: string, c: string) => string)(
        fmt(catC.length), fmt(otherMissing), geoText),
      rows: catC,
    },
    {
      key: 'D', title: t.value.catD, sub: t.value.catDSub,
      rows: rows.filter((l) => ebw.value[l.wals_id] >= 3 && hasWiki(l)
        && l.growth != null && l.baseline_ok).sort(byGrowth),
    },
  ]
})

const sources = computed(() => store.endangermentSources)
const LEVELS_ZH = { 1: '未濒危', 2: '受威胁', 3: '转移中', 4: '垂危', 5: '几近灭绝', 6: '已灭绝' } as const
const LEVELS_EN = { 1: 'not endangered', 2: 'threatened', 3: 'shifting', 4: 'moribund', 5: 'nearly extinct', 6: 'extinct' } as const
const levelName = (lv: number) => (store.lang === 'zh' ? LEVELS_ZH : LEVELS_EN)[lv as 1]

/* ------------------------------------------------------------------ 渲染 */

function render() {
  if (!chart.value) return
  chart.value.setOption({
    grid: { left: 8, right: 22, top: 16, bottom: 28, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        const d = p.data
        const lv = d.value[2]
        const g = d.growth == null ? '—'
          : `${d.growth >= 0 ? '+' : ''}${(d.growth * 100).toFixed(0)}%`
        return `<strong>${d.name}</strong><br>` +
          `<span style="color:${C.textMuted}">${levelName(lv)} · ${t.value.views}</span> ` +
          `${fmt(d.value[1])}<br>` +
          `<span style="color:${C.textMuted}">${t.value.growth}</span> ${g}` +
          (d.baseline_ok === false ? `<br><em style="color:${C.textMuted}">n/a</em>` : '')
      },
    },
    xAxis: {
      type: 'value', min: 0.4, max: 6.6,
      interval: 1,
      axisLabel: {
        formatter: (v: number) => (Number.isInteger(v) && v >= 1 && v <= 6
          ? levelName(v) : ''),
        fontSize: 10,
      },
      splitLine: { show: true, lineStyle: { color: C.border, type: 'dashed' } },
    },
    yAxis: {
      type: 'log', min: 1000,
      axisLabel: { formatter: (v: number) => (v >= 1e6 ? `${v / 1e6}M` : `${v / 1e3}k`) },
    },
    series: [{
      type: 'scatter',
      data: dots.value,
      emphasis: { scale: 1.5 },
      label: {
        show: true, position: 'top', fontSize: 9,
        color: C.textSecondary, distance: 4,
        formatter: (p: any) => (notableSet.value.has(p.data.wals_id) ? p.data.name : ''),
      },
      labelLayout: { hideOverlap: true },
    }],
  }, true)
}

const { schedule } = useChartResize(host, chart)

onMounted(() => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  chart.value.on('click', (p: any) => { if (p.data?.wals_id) store.select(p.data.wals_id) })
  render()
  window.addEventListener('resize', schedule)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', schedule)
  chart.value?.dispose()
})
watch(() => [dots.value, store.lang], render)
</script>

<template>
  <section class="card">
    <header>
      <div>
        <h2>{{ t.title }}</h2>
        <p class="hint">{{ t.sub }}</p>
      </div>
      <span v-if="HAS_DATA" class="cover num">
        AES {{ fmt(sources.aes) }} + UNESCO {{ sources.unescoOnly }}
      </span>
    </header>

    <div v-if="!HAS_DATA" class="empty">{{ t.empty }}</div>

    <template v-else>
      <!-- ① 散点 -->
      <section class="blk">
        <div class="bh">
          <h3>{{ t.scatter }}</h3><span class="sub">{{ t.scatterSub }}</span>
        </div>
        <div ref="host" class="scatter" />
      </section>

      <!-- ② 缺席条：散点图画不出来的那部分 -->
      <section class="blk">
        <div class="bh">
          <h3>{{ t.absence }}</h3><span class="sub warn">{{ t.absenceSub }}</span>
        </div>
        <ul class="abs">
          <li v-for="d in absence" :key="d.lv">
            <span class="dot" :style="{ background: d.color }" />
            <span class="lbl">{{ d.label }}</span>
            <span class="bar">
              <i class="have" :style="{ width: pct(d.rate), background: d.color }" />
            </span>
            <span class="num have-n">{{ fmt(d.wiki) }}</span>
            <span class="num none-n">{{ fmt(d.none) }}</span>
            <span class="num tot">{{ fmt(d.n) }}</span>
          </li>
        </ul>
        <p class="absnote">{{ t.absenceLegend }}</p>
      </section>

      <!-- ③ 值得关注 -->
      <section class="blk">
        <div class="bh">
          <h3>{{ t.watch }}</h3><span class="sub">{{ t.watchSub }}</span>
        </div>
        <div class="cats">
          <div v-for="c in worth" :key="c.key" class="cat">
            <h4>{{ c.title }} <span class="cnt num">{{ fmt(c.rows.length) }}</span></h4>
            <p class="csub">{{ c.sub }}</p>
            <ul>
              <li
                v-for="l in c.rows.slice(0, 5)"
                :key="l.wals_id"
                :class="{ on: store.selected === l.wals_id }"
                @click="store.select(l.wals_id)"
              >
                <span class="nm">{{ langLabel(l) }}</span>
                <span class="num v">{{ l.views_recent ? fmt(Math.round(l.views_recent)) : '—' }}</span>
                <span class="num g" :class="{ up: (l.growth ?? 0) >= 0, dn: (l.growth ?? 0) < 0 }">
                  {{ l.growth != null ? (l.growth >= 0 ? '+' : '') + (l.growth * 100).toFixed(0) + '%' : '' }}
                </span>
              </li>
            </ul>
            <p v-if="c.rows.length > 5" class="more">{{ t.more(fmt(c.rows.length - 5)) }}</p>
          </div>
        </div>
      </section>

      <div class="caveat">
        <h4>{{ t.caveat }}</h4>
        <ul>
          <li>{{ t.caveat1(fmt(sources.aes), fmt(sources.unescoOnly), fmt(sources.none)) }}</li>
          <li>{{ t.caveat2 }}</li>
          <li>{{ t.caveat3 }}</li>
          <li>{{ t.caveat4 }}</li>
        </ul>
      </div>
    </template>
  </section>
</template>

<style scoped>
.card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--sp-4); display: flex; flex-direction: column; gap: var(--sp-4);
  min-height: 0; height: 100%; overflow: hidden auto;
}
header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-3); }
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 0; font-size: var(--fs-small); color: var(--text-muted); }
.cover { font-size: var(--fs-micro); color: var(--text-muted); white-space: nowrap; padding-top: 4px; }
.empty { color: var(--text-muted); font-size: var(--fs-small); padding: var(--sp-5) 0; text-align: center; }

.blk { min-width: 0; }
.bh { display: flex; align-items: baseline; gap: var(--sp-2); margin-bottom: var(--sp-2); flex-wrap: wrap; }
.bh h3 { margin: 0; font-size: var(--fs-small); font-weight: 600; }
.bh .sub { font-size: var(--fs-micro); color: var(--text-muted); }
.bh .sub.warn { color: var(--accent); }

.scatter { height: 340px; width: 100%; }

.abs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.abs li {
  display: grid; grid-template-columns: 8px 84px minmax(60px, 1fr) 52px 52px 56px;
  align-items: center; gap: var(--sp-2);
}
.dot { width: 8px; height: 8px; border-radius: 50%; }
.lbl { font-size: var(--fs-micro); color: var(--text-secondary); white-space: nowrap; }
.bar { height: 13px; background: var(--bg-subtle); border-radius: 7px; overflow: hidden; }
.bar .have { display: block; height: 100%; border-radius: 7px; }
.abs .num { font-size: var(--fs-micro); text-align: right; }
.have-n { color: var(--text-primary); font-weight: 500; }
.none-n { color: var(--text-muted); }
.tot { color: var(--text-muted); }
.absnote { margin: var(--sp-2) 0 0; font-size: var(--fs-micro); color: var(--text-muted); }

.cats { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--sp-3); }
.cat {
  border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: var(--sp-3); background: var(--bg-canvas); min-width: 0;
}
.cat h4 { margin: 0; font-size: var(--fs-micro); font-weight: 600; color: var(--text-primary); }
.cat h4 .cnt { color: var(--accent); }
.csub { margin: 3px 0 var(--sp-2); font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.55; }
.cat ul { list-style: none; margin: 0; padding: 0; }
.cat li {
  display: grid; grid-template-columns: minmax(0, 1fr) 74px 52px;
  gap: var(--sp-2); align-items: baseline;
  padding: 2px 4px; border-radius: var(--radius-sm); cursor: pointer;
}
.cat li:hover { background: var(--bg-subtle); }
.cat li.on { background: var(--accent-soft); }
.nm { font-size: var(--fs-micro); color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cat .num { font-size: var(--fs-micro); text-align: right; }
.cat .v { color: var(--text-primary); }
.cat .g.up { color: var(--positive); }
.cat .g.dn { color: var(--negative); }
.more { margin: 4px 0 0; font-size: var(--fs-micro); color: var(--text-muted); }

.caveat {
  border: 1px solid var(--border); border-top: 3px solid var(--neutral);
  border-radius: var(--radius-md); padding: var(--sp-3); background: var(--bg-canvas);
}
.caveat h4 {
  margin: 0 0 var(--sp-2); font-size: var(--fs-micro); font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted);
}
.caveat ul { margin: 0; padding-left: 1.1em; }
.caveat li { font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.75; }
</style>
