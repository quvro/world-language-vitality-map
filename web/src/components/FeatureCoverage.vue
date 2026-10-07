<script setup lang="ts">
/**
 * 语法特征覆盖率。
 * 这个视图直接决定"条件对比"交互能用哪些特征 —— 覆盖率太低的特征
 * 做分组对比没有意义，所以先把可用性摆出来。
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const host = ref<HTMLDivElement | null>(null)
const chart = shallowRef<any>(null)
const C = semanticColors()
const e = () => (window as any).echarts

/** 在当前筛选出的语言集合上，重新统计每个特征的覆盖数 */
const coverage = computed(() => {
  const m = store.matrix
  if (!m) return []
  const keep = new Set(store.filtered.map((l) => l.wals_id))
  const idx: number[] = []
  m.language_keys.forEach((k, i) => { if (keep.has(k)) idx.push(i) })
  const nameOf = new Map(store.features?.features.map((f) => [f.ID, f.Name]) ?? [])
  return m.feature_ids.map((fid, fi) => {
    let n = 0
    const row = m.values[fi]
    for (const i of idx) if (row[i] != null) n++
    return { fid, name: nameOf.get(fid) || fid, n }
  }).sort((a, b) => b.n - a.n)
})

const usable = computed(() => coverage.value.filter((c) => c.n >= 100).length)

function render() {
  if (!chart.value) return
  const top = coverage.value.slice(0, 20).reverse()
  chart.value.setOption({
    grid: { left: 8, right: 64, top: 10, bottom: 26, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `<strong>${p.name}</strong><br>覆盖 ${p.value.toLocaleString('en-US')} 门语言`,
    },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: top.map((d) => d.name), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar', barWidth: '58%',
      data: top.map((d) => d.n),
      itemStyle: { color: C.accent, opacity: 0.85, borderRadius: [0, 3, 3, 0] },
      label: {
        show: true, position: 'right', fontSize: 10, color: C.textSecondary,
        formatter: (p: any) => p.value.toLocaleString('en-US'),
      },
    }],
  }, true)
}

onMounted(() => {
  if (!host.value) return
  chart.value = e().init(host.value, 'vitality-light')
  render()
  window.addEventListener('resize', resize)
})
function resize() { chart.value?.resize() }
onBeforeUnmount(() => { window.removeEventListener('resize', resize); chart.value?.dispose() })
watch(() => store.filtered, render)
</script>

<template>
  <section class="card">
    <header>
      <h2>语法特征覆盖率</h2>
      <p class="hint">
        当前筛选下，<strong class="num">{{ usable }}</strong> / {{ coverage.length }}
        个特征覆盖 ≥ 100 门语言，可用于分组对比
      </p>
    </header>
    <div ref="host" class="chart" />
    <p class="foot">
      覆盖率 = 有多少门语言在 WALS 里被收录了该特征。空白表示"WALS 未收录"，
      而不是"该语言没有这个特征" —— 分组对比前必须看这个数。
    </p>
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
.hint strong { color: var(--accent); }
.chart { flex: 1; min-height: 400px; }
.foot {
  margin: var(--sp-2) 0 0; padding-top: var(--sp-2);
  border-top: 1px solid var(--border);
  font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.7;
}
</style>
