<script setup lang="ts">
/**
 * 应用外壳：导航布局 + 状态分发。
 *
 * 布局对应设计文档 §6：
 *   顶栏（标题 / 模式 / 全局筛选）
 *   左侧筛选 · 中央主视图（可切换）· 右侧详情
 *   底部时间轴（常驻）
 *   底部 NL 输入（常驻）
 */
import { computed, onMounted } from 'vue'
import { useDataset } from '@/stores/dataset'
import FilterPanel from '@/components/FilterPanel.vue'
import WorldMap from '@/components/WorldMap.vue'
import GrowthChart from '@/components/GrowthChart.vue'
import FeatureCoverage from '@/components/FeatureCoverage.vue'
import LanguageCard from '@/components/LanguageCard.vue'
import VitalityTimeline from '@/components/VitalityTimeline.vue'

const store = useDataset()

const VIEWS = [
  { id: 'map', label: '地图' },
  { id: 'growth', label: '活力变化' },
  { id: 'features', label: '特征' },
] as const

const kpi = computed(() => [
  { v: store.langs.length, l: '语言 / 变体' },
  { v: store.langs.filter((x) => x.latitude).length, l: '有坐标' },
  { v: store.withVitality.length, l: '有维基版本' },
])

onMounted(() => store.load())
</script>

<template>
  <div class="app">
    <header class="top">
      <div class="brand">
        <span class="bar" />
        <div>
          <h1>正在消失的声音</h1>
          <p>数字时代的语言生存图谱</p>
        </div>
      </div>

      <div class="kpis">
        <div v-for="k in kpi" :key="k.l" class="kpi">
          <span class="num v">{{ k.v.toLocaleString('en-US') }}</span>
          <span class="l">{{ k.l }}</span>
        </div>
      </div>

      <div class="modes">
        <button class="mode on">探索模式</button>
        <button class="mode" disabled title="P7 阶段实现">故事模式</button>
      </div>
    </header>

    <main v-if="store.loading" class="state">
      <div class="spinner" />
      <p>正在加载数据集…</p>
    </main>

    <main v-else-if="store.error" class="state err">
      <p><strong>数据加载失败</strong></p>
      <p class="sub">{{ store.error }}</p>
      <p class="sub">
        请确认数据管道已运行：<code>python pipeline/03_build_dataset.py</code>
      </p>
    </main>

    <main v-else class="body">
      <FilterPanel class="col-left" />

      <section class="col-center">
        <nav class="tabs">
          <button
            v-for="v in VIEWS"
            :key="v.id"
            :class="{ on: store.activeView === v.id }"
            @click="store.activeView = v.id"
          >{{ v.label }}</button>
        </nav>
        <div class="stage">
          <WorldMap v-if="store.activeView === 'map'" />
          <GrowthChart v-else-if="store.activeView === 'growth'" />
          <FeatureCoverage v-else />
        </div>
      </section>

      <LanguageCard class="col-right" />
    </main>

    <VitalityTimeline v-if="!store.loading && !store.error" />

    <div class="nl" :class="{ off: true }">
      <span class="ico">💬</span>
      <input
        type="text"
        disabled
        placeholder="用一句话提问，例如「语序是 SOV 且浏览量在增长的语言」"
      >
      <span class="tag">P5 接入大模型</span>
    </div>
  </div>
</template>

<style scoped>
.app { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

/* ---------------------------------------------------------------- 顶栏 */
.top {
  display: flex; align-items: center; gap: var(--sp-5);
  padding: var(--sp-3) var(--sp-5);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
}
.brand { display: flex; align-items: center; gap: var(--sp-3); }
.bar { width: 4px; height: 34px; background: var(--accent); border-radius: var(--radius-pill); }
h1 { margin: 0; font-size: 1.2rem; font-weight: 600; letter-spacing: -0.01em; }
.brand p { margin: 1px 0 0; font-size: var(--fs-micro); color: var(--text-muted); }

.kpis { display: flex; gap: var(--sp-5); margin-left: auto; }
.kpi { text-align: right; }
.kpi .v { display: block; font-size: 1.15rem; font-weight: 600; line-height: 1.1; }
.kpi .l { font-size: var(--fs-micro); color: var(--text-muted); }

.modes { display: flex; border: 1px solid var(--border); border-radius: var(--radius-pill); overflow: hidden; }
.mode {
  border: 0; background: transparent; padding: 5px 14px; cursor: pointer;
  font-family: inherit; font-size: var(--fs-small); color: var(--text-secondary);
}
.mode.on { background: var(--accent); color: var(--text-inverse); }
.mode:disabled { color: var(--text-muted); cursor: not-allowed; }

/* ---------------------------------------------------------------- 主体 */
.body {
  flex: 1; min-height: 0;
  display: grid;
  grid-template-columns: 268px minmax(0, 1fr) 288px;
  gap: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
}
.col-left, .col-right { min-height: 0; }
.col-center { display: flex; flex-direction: column; gap: var(--sp-3); min-width: 0; min-height: 0; }

.tabs { display: flex; gap: var(--sp-1); }
.tabs button {
  border: 0; background: transparent; cursor: pointer; font-family: inherit;
  padding: 6px 14px; border-radius: var(--radius-pill);
  font-size: var(--fs-small); color: var(--text-secondary);
  transition: background var(--dur-fast) var(--ease-out);
}
.tabs button:hover { background: var(--bg-subtle); }
.tabs button.on { background: var(--text-primary); color: var(--text-inverse); }

.stage { flex: 1; min-height: 0; }

/* ------------------------------------------------------------ 状态页 */
.state { flex: 1; display: grid; place-content: center; justify-items: center; gap: var(--sp-3); color: var(--text-secondary); }
.state .sub { margin: 0; font-size: var(--fs-small); color: var(--text-muted); }
.state code { background: var(--bg-subtle); padding: 2px 6px; border-radius: var(--radius-sm); }
.state.err strong { color: var(--negative); }
.spinner {
  width: 26px; height: 26px; border-radius: 50%;
  border: 2px solid var(--border); border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ------------------------------------------------------------ NL 入口 */
.nl {
  display: flex; align-items: center; gap: var(--sp-3);
  padding: var(--sp-2) var(--sp-5);
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
}
.nl .ico { font-size: 14px; opacity: 0.7; }
.nl input {
  flex: 1; border: 0; background: transparent;
  font-family: inherit; font-size: var(--fs-small); color: var(--text-primary);
  padding: 6px 0;
}
.nl input::placeholder { color: var(--text-muted); }
.tag {
  font-size: var(--fs-micro); color: var(--text-muted);
  border: 1px solid var(--border); border-radius: var(--radius-pill);
  padding: 2px 9px; white-space: nowrap;
}

@media (max-width: 1200px) {
  .body { grid-template-columns: 240px minmax(0, 1fr); }
  .col-right { display: none; }
  .kpis { display: none; }
}
</style>
