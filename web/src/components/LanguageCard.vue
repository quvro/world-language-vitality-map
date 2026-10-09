<script setup lang="ts">
/**
 * 右侧详情卡。显示选中语言的结构特征与十年曲线。
 * 曲线是手写 SVG —— 单条 mini 折线不值得起一个 ECharts 实例。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const { family: familyLabel, language: langLabel } = useDisplayNames()
const C = semanticColors()
const lang = computed(() => store.selectedLanguage)
const displayName = computed(() => (lang.value ? langLabel(lang.value) : ''))

const T = {
  zh: {
    close: '取消选中',
    growthTitle: '十年浏览趋势',
    unreliable: '（基线低，不可信）',
    noSeries: '该语言没有对应的维基百科版本，因此没有时间序列。',
    fFamily: '语系', fSub: '语族', fGenus: '属', fArea: '语区',
    fIso: 'ISO 639-3', fGlotto: 'Glottocode', fWiki: '维基版本',
    none: '无',
    addCompare: '加入对比', removeCompare: '移出对比',
    emptyTitle: '点一个点看看',
    emptyBody: '地图上的每一颗点都是一门语言。点击后这里会显示它的结构特征与十年活力曲线。',
  },
  en: {
    close: 'Deselect',
    growthTitle: 'Ten-year view trend',
    unreliable: '(weak baseline, unreliable)',
    noSeries: 'This language has no Wikipedia edition, so there is no time series.',
    fFamily: 'Family', fSub: 'Subfamily', fGenus: 'Genus', fArea: 'Area',
    fIso: 'ISO 639-3', fGlotto: 'Glottocode', fWiki: 'Wikipedia',
    none: 'none',
    addCompare: 'Add to comparison', removeCompare: 'Remove from comparison',
    emptyTitle: 'Click a dot',
    emptyBody: 'Every dot on the map is a language. Click one to see its structural profile and ten-year vitality curve here.',
  },
} as const
const t = computed(() => T[store.lang])

const series = computed(() => {
  const l = lang.value
  if (!l?.wiki_code || !store.timeseries) return null
  const s = store.timeseries.by_language[l.wals_id]
  if (!s) return null
  const months = Object.keys(s.views).sort()
  if (!months.length) return null
  return { months, values: months.map((m) => s.views[m] ?? 0) }
})

/** 折线路径；首尾各留 2px 余量 */
const path = computed(() => {
  const s = series.value
  if (!s || s.values.length < 2) return { line: '', area: '' }
  const W = 260, H = 56
  const max = Math.max(...s.values, 1)
  const pts = s.values.map((v, i) => {
    const x = (i / (s.values.length - 1)) * W
    const y = H - 3 - (v / max) * (H - 8)
    return [x, y] as const
  })
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return { line, area: `${line} L${W},${H} L0,${H} Z` }
})

const growthText = computed(() => {
  const g = lang.value?.growth
  if (g == null) return null
  return {
    v: `${g >= 0 ? '+' : ''}${(g * 100).toFixed(1)}%`,
    up: g >= 0,
    ok: lang.value?.baseline_ok,
  }
})

const facts = computed(() => {
  const l = lang.value
  if (!l) return [] as [string, string][]
  return [
    [t.value.fFamily, familyLabel(l.family)],
    [t.value.fSub, l.subfamily || '—'],
    [t.value.fGenus, l.genus || '—'],
    [t.value.fArea, l.macroarea || '—'],
    [t.value.fIso, l.iso639p3 || '—'],
    ['WALS ID', l.wals_id],
    [t.value.fGlotto, l.glottocode || '—'],
    [t.value.fWiki, l.wiki_code ? `${l.wiki_code}.wikipedia` : t.value.none],
  ] as [string, string][]
})
</script>

<template>
  <aside class="card">
    <template v-if="lang">
      <header>
        <h2>{{ displayName }}</h2>
        <button class="x" :title="t.close" @click="store.select(null)">×</button>
      </header>

      <div v-if="growthText" class="growth" :class="{ neg: !growthText.up }">
        <span class="num v">{{ growthText.v }}</span>
        <span class="k">{{ t.growthTitle }}
          <template v-if="!growthText.ok">{{ t.unreliable }}</template>
        </span>
      </div>

      <div v-if="series" class="sparkwrap">
        <svg viewBox="0 0 260 56" preserveAspectRatio="none" aria-hidden="true">
          <path :d="path.area" :fill="growthText?.up ? C.positive : C.negative" opacity="0.13" />
          <path :d="path.line" :stroke="growthText?.up ? C.positive : C.negative"
                stroke-width="1.6" fill="none" />
        </svg>
        <div class="axis num">
          <span>{{ series.months[0]?.slice(0, 4) }}</span>
          <span>{{ series.months[series.months.length - 1]?.slice(0, 4) }}</span>
        </div>
      </div>
      <p v-else class="none">{{ t.noSeries }}</p>

      <dl class="facts">
        <template v-for="[k, v] in facts" :key="k">
          <dt>{{ k }}</dt><dd>{{ v }}</dd>
        </template>
      </dl>

      <button class="cmp" @click="store.toggleComparison(lang.wals_id)">
        {{ store.comparisonSet.includes(lang.wals_id) ? t.removeCompare : t.addCompare }}
        <span v-if="store.comparisonSet.length" class="num">
          ({{ store.comparisonSet.length }}/4)
        </span>
      </button>
    </template>

    <div v-else class="empty">
      <div class="ring" />
      <p><strong>{{ t.emptyTitle }}</strong></p>
      <p class="sub">{{ t.emptyBody }}</p>
    </div>
  </aside>
</template>

<style scoped>
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  overflow: hidden auto;
  min-height: 0; height: 100%;
}
header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-2); }
h2 { margin: 0; font-size: 1.15rem; font-weight: 600; line-height: 1.3; }
.x {
  border: 0; background: transparent; cursor: pointer; font-size: 18px;
  color: var(--text-muted); line-height: 1; padding: 0 2px;
}
.x:hover { color: var(--text-primary); }

.growth {
  margin: var(--sp-3) 0 var(--sp-2);
  padding: var(--sp-3);
  background: var(--positive-soft); border-radius: var(--radius-md);
}
.growth.neg { background: var(--negative-soft); }
.growth .v { font-size: 1.5rem; font-weight: 600; color: var(--positive); display: block; }
.growth.neg .v { color: var(--negative); }
.growth .k { font-size: var(--fs-micro); color: var(--text-secondary); }

.sparkwrap { margin: var(--sp-2) 0 var(--sp-3); }
.sparkwrap svg { width: 100%; height: 56px; display: block; }
.axis { display: flex; justify-content: space-between; font-size: var(--fs-micro); color: var(--text-muted); }
.none { font-size: var(--fs-small); color: var(--text-muted); line-height: 1.6; }

.facts {
  display: grid; grid-template-columns: auto 1fr;
  gap: 5px var(--sp-3); margin: 0; font-size: var(--fs-small);
}
.facts dt { color: var(--text-muted); }
.facts dd { margin: 0; color: var(--text-primary); word-break: break-all; }

.cmp {
  margin-top: var(--sp-4); width: 100%;
  padding: 7px; border-radius: var(--radius-md); cursor: pointer;
  border: 1px solid var(--border-strong); background: var(--bg-surface);
  color: var(--text-primary); font-family: inherit; font-size: var(--fs-small);
  transition: background var(--dur-fast) var(--ease-out);
}
.cmp:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.empty { text-align: center; padding: var(--sp-5) var(--sp-2); }
.empty .ring {
  width: 46px; height: 46px; margin: 0 auto var(--sp-3);
  border: 2px dashed var(--border-strong); border-radius: 50%;
}
.empty p { margin: 0; font-size: var(--fs-small); }
.empty .sub { margin-top: var(--sp-2); color: var(--text-muted); line-height: 1.7; }
</style>
