<script setup lang="ts">
/**
 * 底部常驻时间轴 —— 签名交互之一，手写而非用组件库。
 *
 * 它是「全局变量」：切换主视图时不该消失。拖动或播放会改写 store.monthIndex，
 * 所有订阅当前月份的视图随之联动。
 *
 * 与地图的咬合：
 *   活力层在地图上永远在线、大小由本时间轴驱动，所以拖动**一定**有可见反馈
 *   （早期版本存在一个没有时间编码的「分布」模式，在那里拖时间轴毫无反应，
 *   那是设计缺陷，已通过去掉模式划分解决）。
 *   选中某门语言后，时间轴上会画出**它自己的数据覆盖区间** ——
 *   有些维基是 2019 年之后才被统计的，看到区间才不会误读它的曲线。
 *
 * 上方折线是全部语言当月浏览量的合计，给时间轴一个「地形」参照。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useDataset } from '@/stores/dataset'
import { semanticColors } from '@/theme/echarts-theme.js'

const store = useDataset()
const C = semanticColors()
const timer = ref<number | null>(null)

const months = computed(() => store.months)
const idx = computed(() => store.monthIndex)

const totals = computed(() => {
  const ts = store.timeseries?.by_language
  if (!ts) return [] as number[]
  return months.value.map((m) => {
    let sum = 0
    for (const s of Object.values(ts)) sum += s.views[m] ?? 0
    return sum
  })
})

const spark = computed(() => {
  const t = totals.value
  const max = Math.max(...t, 1)
  const W = 1000
  const H = 34
  if (!t.length) return { line: '', area: '' }
  const pts = t.map((v, i) => {
    const x = (i / Math.max(t.length - 1, 1)) * W
    const y = H - (v / max) * (H - 4) - 2
    return [x, y] as const
  })
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return { line, area: `${line} L${W},${H} L0,${H} Z` }
})

const pct = computed(() =>
  months.value.length > 1 ? (idx.value / (months.value.length - 1)) * 100 : 100
)

const label = computed(() => {
  const m = store.currentMonth
  return m ? `${m.slice(0, 4)} 年 ${Number(m.slice(4, 6))} 月` : '—'
})

/** 选中语言在全局时间轴上的覆盖区间 —— 避免误读只有几年数据的语言。 */
const selBand = computed(() => {
  const l = store.selectedLanguage
  if (!l?.wiki_code || !store.timeseries) return null
  const s = store.timeseries.by_language[l.wals_id]
  if (!s) return null
  const own = Object.keys(s.views).sort()
  const all = months.value
  if (!own.length || !all.length) return null
  const i0 = all.indexOf(own[0])
  const i1 = all.indexOf(own[own.length - 1])
  if (i0 < 0 || i1 < 0) return null
  const n = Math.max(all.length - 1, 1)
  return {
    left: (i0 / n) * 100,
    width: ((i1 - i0) / n) * 100,
    months: own.length,
    name: l.name,
    partial: own.length < all.length,
  }
})

function stop() {
  if (timer.value != null) { clearInterval(timer.value); timer.value = null }
  store.playing = false
}

function play() {
  if (timer.value != null) { stop(); return }
  store.playing = true
  timer.value = window.setInterval(() => {
    if (store.monthIndex >= months.value.length - 1) store.monthIndex = 0
    else store.setMonthIndex(store.monthIndex + 1)
  }, 110)
}

function onInput(ev: Event) {
  stop()
  store.setMonthIndex(Number((ev.target as HTMLInputElement).value))
}

onBeforeUnmount(stop)
watch(() => months.value.length, stop)
</script>

<template>
  <footer class="timeline" :class="{ disabled: !months.length }">
    <div class="left">
      <button
        class="play" :disabled="!months.length"
        :title="store.playing ? '暂停' : '播放十年变化'"
        @click="play"
      >
        <span v-if="!store.playing">▶</span><span v-else>❚❚</span>
      </button>
      <div class="stamp">
        <div class="m num">{{ label }}</div>
        <div class="k">时间轴 · {{ months.length }} 个月</div>
      </div>
    </div>

    <div class="track">
      <svg class="spark" viewBox="0 0 1000 34" preserveAspectRatio="none" aria-hidden="true">
        <path :d="spark.area" :fill="C.accent" opacity="0.10" />
        <path :d="spark.line" :stroke="C.accent" :stroke-width="1.6" fill="none" opacity="0.55" />
      </svg>

      <!-- 选中语言的可用区间 -->
      <div
        v-if="selBand"
        class="band"
        :class="{ partial: selBand.partial }"
        :style="{ left: selBand.left + '%', width: Math.max(selBand.width, 0.6) + '%' }"
        :title="`${selBand.name} 在这段时间内有数据（${selBand.months} 个月）`"
      />

      <div class="head" :style="{ left: pct + '%' }" />
      <input
        class="range" type="range"
        :min="0" :max="Math.max(months.length - 1, 0)" :value="idx"
        :disabled="!months.length" aria-label="选择月份"
        @input="onInput"
      >
    </div>

    <div class="right">
      <span v-if="selBand" class="tip">
        选中：<strong>{{ selBand.name }}</strong> ·
        <span :class="{ warn: selBand.partial }">{{ selBand.months }} 个月数据</span>
      </span>
      <span v-else class="tip">拖动或播放，地图上的点随之长缩</span>
    </div>
  </footer>
</template>

<style scoped>
.timeline {
  display: grid;
  grid-template-columns: 240px 1fr 250px;
  align-items: center;
  gap: var(--sp-4);
  padding: var(--sp-3) var(--sp-5);
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
}
.timeline.disabled { opacity: 0.55; }

.left { display: flex; align-items: center; gap: var(--sp-3); }
.play {
  width: 34px; height: 34px; border-radius: 50%; flex: none;
  border: 1px solid var(--border-strong); background: var(--bg-surface);
  color: var(--accent); cursor: pointer; font-size: 12px;
  display: grid; place-items: center;
  transition: background var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out);
}
.play:hover:not(:disabled) { background: var(--accent-soft); transform: scale(1.06); }
.play:disabled { cursor: not-allowed; color: var(--text-muted); }

.stamp .m { font-size: 1rem; font-weight: 600; letter-spacing: -0.01em; }
.stamp .k { font-size: var(--fs-micro); color: var(--text-muted); }

.track { position: relative; height: 44px; }
.spark { position: absolute; inset: 5px 0; width: 100%; height: 34px; }

.band {
  position: absolute; top: 2px; bottom: 2px;
  background: var(--accent); opacity: 0.14;
  border-radius: var(--radius-sm); pointer-events: none;
}
.band.partial { opacity: 0.22; }

.head {
  position: absolute; top: 0; bottom: 0; width: 2px;
  background: var(--accent); border-radius: 1px;
  transform: translateX(-1px); pointer-events: none;
}

.range {
  position: absolute; inset: 0; width: 100%; height: 100%;
  margin: 0; background: transparent; cursor: pointer;
  -webkit-appearance: none; appearance: none;
}
.range:disabled { cursor: not-allowed; }
.range::-webkit-slider-runnable-track { height: 100%; background: transparent; }
.range::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 14px; height: 44px; border-radius: var(--radius-sm);
  background: transparent; border: 0;
}
.range::-moz-range-track { height: 100%; background: transparent; }
.range::-moz-range-thumb { width: 14px; height: 44px; border: 0; background: transparent; }

.right { text-align: right; }
.tip { font-size: var(--fs-micro); color: var(--text-muted); }
.tip.switch { color: var(--accent); }
.tip .warn { color: var(--negative); }
.tip strong { color: var(--text-primary); }

@media (max-width: 900px) {
  .timeline { grid-template-columns: 1fr; gap: var(--sp-2); }
  .right { display: none; }
}
</style>
