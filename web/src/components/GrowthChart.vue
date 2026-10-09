<script setup lang="ts">
/**
 * 十年活力变化：跌幅榜与涨幅榜并置，正面回答"谁在退、谁在进"。
 *
 * 修过一个真实的 off-by-one：早期写成 `[...r.slice(0,9), ...r.slice(-9)]`，
 * 当可分析语言少于 18 个时两个切片会**重叠**，同一门语言于是显示两次。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const { language: langLabel } = useDisplayNames()
const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)
const C = semanticColors()
const e = () => (window as any).echarts

const T = {
  zh: {
    title: '十年数字活力变化',
    hint: (n: string) => `首 3 月均值 → 末 3 月均值 · 当前筛选下共 ${n} 门语言可分析`,
    empty: '当前筛选下可分析的语言太少（少于 4 门），放宽筛选后再看。',
    views: '次/月',
  },
  en: {
    title: 'Ten-year digital vitality',
    hint: (n: string) => `first 3-month mean → last 3-month mean · ${n} languages analysable with current filters`,
    empty: 'Too few analysable languages (under 4) for the current filters.',
    views: 'views/mo',
  },
} as const
const t = computed(() => T[store.lang])

const ranked = computed(() =>
  store.filtered
    .filter((l) => l.baseline_ok && l.growth != null)
    .slice()
    .sort((a, b) => a.growth! - b.growth!)
)

const K = 9

/** 取两端各 K 个；总量不足 2K 时直接全取，避免两个切片重叠导致重复 */
const picked = computed(() => {
  const r = ranked.value
  if (r.length <= K * 2) return r.slice()
  return [...r.slice(0, K), ...r.slice(-K)]
})

function render() {
  if (!chart.value) return
  const rows = picked.value
  chart.value.setOption({
    grid: { left: 8, right: 64, top: 10, bottom: 26, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: any) =>
        `<strong>${p.name}</strong><br>` +
        `${Math.round(p.data.from).toLocaleString('en-US')} → ` +
        `${Math.round(p.data.to).toLocaleString('en-US')} ${t.value.views}<br>` +
        `<span style="color:${p.value >= 0 ? C.positive : C.negative};font-weight:600">` +
        `${p.value >= 0 ? '+' : ''}${p.value}%</span>`,
    },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: {
      type: 'category',
      data: rows.map((d) => langLabel(d)),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      barWidth: '60%',
      data: rows.map((d) => {
        const isSel = store.selected === d.wals_id
        return {
          value: Number((d.growth! * 100).toFixed(1)),
          from: d.views_baseline, to: d.views_recent, wals_id: d.wals_id,
          itemStyle: {
            color: d.growth! >= 0 ? C.positive : C.negative,
            opacity: store.selected && !isSel ? 0.3 : 1,
            borderColor: isSel ? C.textPrimary : 'transparent',
            borderWidth: isSel ? 2 : 0,
            borderRadius: d.growth! >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3],
          },
        }
      }),
      label: {
        show: true, position: 'right', fontSize: 10,
        fontFamily: 'JetBrains Mono, Consolas, monospace',
        color: C.textSecondary,
        formatter: (p: any) => `${p.value >= 0 ? '+' : ''}${p.value}%`,
      },
    }],
  }, true)
}

onMounted(() => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  chart.value.on('click', (p: any) => { if (p.data?.wals_id) store.select(p.data.wals_id) })
  render()
  window.addEventListener('resize', resize)
})
function resize() { chart.value?.resize() }
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart.value?.dispose() })

watch(() => [store.filtered, store.selected, store.lang], render)
</script>

<template>
  <section class="card">
    <header>
      <h2>{{ t.title }}</h2>
      <p class="hint">{{ t.hint(ranked.length.toLocaleString('en-US')) }}</p>
    </header>
    <div v-if="ranked.length < 4" class="empty">{{ t.empty }}</div>
    <div v-show="ranked.length >= 4" ref="host" class="chart" />
  </section>
</template>

<style scoped>
.card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--sp-4); display: flex; flex-direction: column;
  min-height: 0; height: 100%;
}
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 var(--sp-2); font-size: var(--fs-small); color: var(--text-muted); }
.chart { flex: 1; min-height: 300px; }
.empty { flex: 1; display: grid; place-items: center; color: var(--text-muted); font-size: var(--fs-small); }
</style>
