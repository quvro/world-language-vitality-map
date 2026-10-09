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
import { computed, onMounted, ref } from 'vue'
import { useDataset } from '@/stores/dataset'
import FilterPanel from '@/components/FilterPanel.vue'
import WorldMap from '@/components/WorldMap.vue'
import GrowthChart from '@/components/GrowthChart.vue'
import FeatureCompare from '@/components/FeatureCompare.vue'
import LanguageCard from '@/components/LanguageCard.vue'
import VitalityTimeline from '@/components/VitalityTimeline.vue'
import NlQuery from '@/components/NlQuery.vue'

const store = useDataset()

const T = {
  zh: {
    title: '世界语言赛博活力图谱',
    subtitle: '数字时代的语言生存图谱',
    explore: '探索模式', story: '故事模式',
    vMap: '地图', vGrowth: '活力变化', vCompare: '条件对比',
    kLang: '语言 / 变体', kCoord: '有坐标', kWiki: '有维基版本',
    loading: '正在加载数据集…',
    errTitle: '数据加载失败', errHint: '请确认数据管道已运行：',
    nlPlaceholder: '用一句话提问，例如「语序是 SOV 且浏览量在增长的语言」',
    nlTag: 'P5 接入大模型', storyTag: 'P7 阶段实现',
    toggleLang: 'EN',
    collapse: '收起详情面板', expand: '展开详情面板',
  },
  en: {
    title: 'Cyber-Vitality Atlas of World Languages',
    subtitle: 'How languages survive in the digital age',
    explore: 'Explore', story: 'Story',
    vMap: 'Map', vGrowth: 'Vitality', vCompare: 'Comparison',
    kLang: 'languages', kCoord: 'mapped', kWiki: 'with Wikipedia',
    loading: 'Loading dataset…',
    errTitle: 'Failed to load data', errHint: 'Run the data pipeline first:',
    nlPlaceholder: 'Ask in one sentence, e.g. “SOV languages whose traffic is growing”',
    nlTag: 'LLM in P5', storyTag: 'planned for P7',
    toggleLang: '中文',
    collapse: 'Collapse detail panel', expand: 'Expand detail panel',
  },
} as const

const t = computed(() => T[store.lang])

const VIEWS = computed(() => [
  { id: 'map', label: t.value.vMap },
  { id: 'growth', label: t.value.vGrowth },
  { id: 'features', label: t.value.vCompare },
] as const)

const kpi = computed(() => [
  { v: store.langs.length, l: t.value.kLang },
  { v: store.langs.filter((x) => x.latitude).length, l: t.value.kCoord },
  { v: store.withVitality.length, l: t.value.kWiki },
])

function toggleLang() {
  store.lang = store.lang === 'zh' ? 'en' : 'zh'
}

/** 右栏可折叠：小屏幕或只想看地图时把它收起来，箭头是唯一的交互控件 */
const rightOpen = ref(true)

onMounted(() => store.load())
</script>

<template>
  <div class="app">
    <header class="top">
      <div class="brand">
        <span class="bar" />
        <div>
          <h1>{{ t.title }}</h1>
          <p>{{ t.subtitle }}</p>
        </div>
      </div>

      <div class="kpis">
        <div v-for="k in kpi" :key="k.l" class="kpi">
          <span class="num v">{{ k.v.toLocaleString('en-US') }}</span>
          <span class="l">{{ k.l }}</span>
        </div>
      </div>

      <div class="modes">
        <button class="mode on">{{ t.explore }}</button>
        <button class="mode" disabled :title="t.storyTag">{{ t.story }}</button>
        <button class="lang" :title="t.toggleLang" @click="toggleLang">{{ t.toggleLang }}</button>
      </div>
    </header>

    <main v-if="store.loading" class="state">
      <div class="spinner" />
      <p>{{ t.loading }}</p>
    </main>

    <main v-else-if="store.error" class="state err">
      <p><strong>{{ t.errTitle }}</strong></p>
      <p class="sub">{{ store.error }}</p>
      <p class="sub">
        {{ t.errHint }}<code>python pipeline/03_build_dataset.py</code>
      </p>
    </main>

    <main v-else class="body" :class="{ 'right-collapsed': !rightOpen }">
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
          <FeatureCompare v-else />
        </div>
      </section>

      <div class="col-right" :class="{ collapsed: !rightOpen }">
        <button
          class="handle"
          :title="rightOpen ? t.collapse : t.expand"
          :aria-expanded="rightOpen"
          @click="rightOpen = !rightOpen"
        >
          <span class="arrow" :class="{ flipped: !rightOpen }">›</span>
        </button>
        <!-- 卡片常驻 DOM：折叠时靠位移+淡出，展开时滑回来，而不是显示/隐藏切换 -->
        <div class="card-wrap">
          <LanguageCard />
        </div>
      </div>
    </main>

    <VitalityTimeline v-if="!store.loading && !store.error" />

    <NlQuery v-if="!store.loading && !store.error" />
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

/* 中英切换：做成一个明确的文字按钮，而不是图标（不需要猜） */
.lang {
  margin-left: var(--sp-2);
  border: 1px solid var(--border-strong); background: var(--bg-surface);
  color: var(--text-primary); cursor: pointer;
  padding: 5px 12px; border-radius: var(--radius-pill);
  font-family: inherit; font-size: var(--fs-small); font-weight: 500;
  transition: background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.lang:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

/* ---------------------------------------------------------------- 主体 */
.body {
  flex: 1; min-height: 0;
  display: grid;
  /* 左栏加宽：筛选面板里的语系列表需要更宽才能不挤 */
  grid-template-columns: 310px minmax(0, 1fr) 288px;
  gap: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
  /* 折叠时列宽平滑过渡，而不是瞬间跳变 */
  transition: grid-template-columns var(--dur-base) var(--ease-in-out);
}
.col-left, .col-right { min-height: 0; }
.col-center { display: flex; flex-direction: column; gap: var(--sp-3); min-width: 0; min-height: 0; }

/* 右栏：一个窄把手 + 卡片。折叠时列宽收到把手宽度 */
.col-right {
  display: flex; align-items: stretch; gap: var(--sp-2);
  min-width: 0; min-height: 0;
  /* 折叠过程中卡片会被压窄，裁掉溢出避免它"漏"到地图上 */
  overflow: hidden;
}
.handle {
  flex: none; width: 18px; padding: 0; cursor: pointer;
  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-surface); color: var(--text-muted);
  display: grid; place-items: center;
  transition: background var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.handle:hover { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); }
.handle .arrow {
  font-size: 15px; line-height: 1;
  transition: transform var(--dur-base) var(--ease-out);
}
.handle .arrow.flipped { transform: rotate(180deg); }

/* 卡片本体用「平移 + 淡出」进出，产生滑动的感觉 */
.card-wrap {
  flex: 1; min-width: 0; min-height: 0;
  transition: opacity var(--dur-base) var(--ease-out),
              transform var(--dur-base) var(--ease-out);
}
.col-right.collapsed .card-wrap {
  opacity: 0;
  transform: translateX(32px);
  pointer-events: none;
}

/* 折叠后只留把手那一条 */
.body.right-collapsed { grid-template-columns: 310px minmax(0, 1fr) 24px; }

/* 尊重系统的减少动效偏好 */
@media (prefers-reduced-motion: reduce) {
  .body, .card-wrap, .handle .arrow { transition: none; }
}

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

/* NL 查询条在 NlQuery 组件内部自带样式，这里不再重复定义 */

@media (max-width: 1200px) {
  .body { grid-template-columns: 240px minmax(0, 1fr); }
  .col-right { display: none; }
  .kpis { display: none; }
}
</style>
