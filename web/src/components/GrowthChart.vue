<script setup lang="ts">
/** 十年活力变化：跌幅榜与涨幅榜并置，正面回答"谁在退、谁在进"。 */
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

const ranked = computed(() => {
  const ok = store.filtered.filter((l) => l.baseline_ok && l.growth != null)
  return ok.sort((a, b) => (a.growth! - b.growth!))
})

function render() {
  if (!chart.value) return
  const r = ranked.value
  const picked = [...r.slice(0, 9), ...r.slice(-9)].sort(
    (a, b) => a.growth! - b.growth!
  )
  chart.value.setOption({
    grid: { left: 8, right: 64, top: 10, bottom: 26, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: any) =>
        `<strong>${p.name}</strong><br>` +
        `${Math.round(p.data.from).toLocaleString('en-US')} → ` +
        `${Math.round(p.data.to).toLocaleString('en-US')} 次/月<br>` +
        `<span style="color:${p.value >= 0 ? C.positive : C.negative};font-weight:600">` +
        `${p.value >= 0 ? '+' : ''}${p.value}%</span>`,
    },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: {
      type: 'category',
      data: picked.map((d) => langLabel(d)),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      barWidth: '60%',
      data: picked.map((d) => {
        const isSel = store.selected === d.wals_id
        return {
          value: Number((d.growth! * 100).toFixed(1)),
          from: d.views_baseline, to: d.views_recent, wals_id: d.wals_id,
          itemStyle: {
            color: d.growth! >= 0 ? C.positive : C.negative,
            opacity: store.selected && !isSel ? 0.35 : 1,
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
watch(() => [store.filtered, store.selected], render)
</script>

<template>
  <section class="card">
    <header>
      <h2>十年数字活力变化</h2>
      <p class="hint">
        首 3 月均值 → 末 3 月均值 · 当前筛选下共
        <strong class="num">{{ ranked.length.toLocaleString('en-US') }}</strong> 门语言可用
      </p>
    </header>
    <div v-if="ranked.length < 4" class="empty">
      当前筛选下可分析的语言太少，放宽筛选后再看。
    </div>
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
.hint strong { color: var(--accent); }
.chart { flex: 1; min-height: 420px; }
.empty { flex: 1; display: grid; place-items: center; color: var(--text-muted); font-size: var(--fs-small); }
</style>
