<script setup lang="ts">
/**
 * 左侧筛选面板。
 *
 * 布局上刻意去掉了几样东西：
 *   · 语系搜索框 —— 语系列表本身就短，加搜索框反而挤占列表高度，
 *     结果一次只能看到三四行
 *   · 「命中 N / M」与说明文字 —— 移到时间轴那一行，把纵向空间还给列表
 * 标题不再用 h3 + 行内 span：那会让「点击筛选，可多选」跟标题挤在一行里叠字，
 * 现在改成 flex 两端对齐。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { MACRO_AREAS, type MacroArea } from '@/types'
import { categoryPalette } from '@/theme/echarts-theme.js'

const store = useDataset()
const { macro: macroLabel, family: familyLabel } = useDisplayNames()
const PALETTE = categoryPalette()

const T = {
  zh: {
    filters: '筛选', clear: '清空', area: '语区', family: '语系',
    multi: '可多选', search: '搜索语言名（中英文均可）',
    reliability: '数据可信度', reliableOnly: '只看基线可靠的语言',
    reliableNote: '部分小语种维基在早期几乎没有记录，后来才有流量。它们的"增长率"是统计伪影，勾选此项可排除。',
  },
  en: {
    filters: 'Filters', clear: 'Clear', area: 'Area', family: 'Family',
    multi: 'multi-select', search: 'Search language (Chinese or English)',
    reliability: 'Reliability', reliableOnly: 'Reliable baseline only',
    reliableNote: 'Some small wikis had almost no recorded traffic early on and only later gained visitors. Their "growth" is a measurement artefact; this excludes them.',
  },
} as const

const t = computed(() => T[store.lang])

const activeCount = computed(() =>
  store.macroAreas.length + store.families.length +
  (store.onlyReliable ? 1 : 0) + (store.search ? 1 : 0) +
  (store.featureFilter ? 1 : 0)
)
</script>

<template>
  <aside class="panel">
    <div class="head">
      <h2>{{ t.filters }}</h2>
      <button v-if="activeCount" class="clear" @click="store.clearFilters()">
        {{ t.clear }} {{ activeCount }}
      </button>
    </div>

    <label class="search">
      <input v-model="store.search" type="search" :placeholder="t.search">
    </label>

    <section class="block">
      <div class="sh">
        <h3>{{ t.area }}</h3><span class="tip">{{ t.multi }}</span>
      </div>
      <div class="chips">
        <button
          v-for="(m, i) in MACRO_AREAS"
          :key="m"
          class="chip"
          :class="{ on: store.macroAreas.includes(m) }"
          :style="store.macroAreas.includes(m)
            ? { background: PALETTE[i], borderColor: PALETTE[i], color: '#fff' } : {}"
          @click="store.toggleMacroArea(m as MacroArea)"
        >
          <i :style="{ background: store.macroAreas.includes(m) ? '#fff' : PALETTE[i] }" />{{ macroLabel(m) }}
        </button>
      </div>
    </section>

    <section class="block grow">
      <div class="sh">
        <h3>{{ t.family }}</h3>
        <span class="tip">{{ store.familyList.length }}</span>
      </div>
      <ul class="fams">
        <li v-for="f in store.familyList" :key="f.family">
          <button
            :class="{ on: store.families.includes(f.family) }"
            @click="store.toggleFamily(f.family)"
          >
            <span class="nm">{{ familyLabel(f.family) }}</span>
            <span class="ct num">{{ f.count }}</span>
          </button>
        </li>
      </ul>
    </section>

    <section class="block">
      <div class="sh"><h3>{{ t.reliability }}</h3></div>
      <label class="toggle">
        <input v-model="store.onlyReliable" type="checkbox">
        <span>{{ t.reliableOnly }}</span>
      </label>
      <p class="note">{{ t.reliableNote }}</p>
    </section>
  </aside>
</template>

<style scoped>
.panel {
  display: flex; flex-direction: column; gap: var(--sp-3);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  overflow: hidden;
  min-height: 0; height: 100%;
}
.head { display: flex; align-items: baseline; justify-content: space-between; flex: none; }
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }

/* 标题行用 flex 两端对齐 —— 之前 span 直接跟在标题后面会挤在一行叠字 */
.sh {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: var(--sp-2); margin-bottom: var(--sp-2);
}
h3 {
  margin: 0; font-size: var(--fs-micro); text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600;
}
.sh .tip {
  font-size: var(--fs-micro); color: var(--text-muted);
  text-transform: none; letter-spacing: 0; white-space: nowrap;
}
.clear {
  border: 0; background: transparent; color: var(--accent);
  font-size: var(--fs-small); cursor: pointer; font-family: inherit;
}
.clear:hover { text-decoration: underline; }

.search { flex: none; }
.search input {
  width: 100%; padding: 7px 11px;
  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-canvas); color: var(--text-primary);
  font-family: inherit; font-size: var(--fs-small);
}
.search input:focus { outline: 2px solid var(--focus-ring); outline-offset: 1px; }

.block { flex: none; min-height: 0; }
.block.grow { flex: 1; display: flex; flex-direction: column; min-height: 0; }

.chips { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; font-size: var(--fs-small); font-family: inherit;
  border: 1px solid var(--border); border-radius: var(--radius-pill);
  background: var(--bg-surface); color: var(--text-secondary); cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out);
}
.chip:hover { background: var(--bg-subtle); }
.chip.on { font-weight: 500; }
.chip i { width: 7px; height: 7px; border-radius: 50%; flex: none; }

/* 语系列表拿满剩余高度（这是去掉搜索框换来的） */
.fams {
  list-style: none; margin: 0; padding: 0;
  overflow: auto; flex: 1; min-height: 120px;
}
.fams button {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: var(--sp-2);
  width: 100%; border: 0; background: transparent; cursor: pointer;
  padding: 3px 6px; border-radius: var(--radius-sm);
  font-family: inherit; font-size: var(--fs-small); color: var(--text-secondary);
  text-align: left; line-height: 1.5;
}
.fams button:hover { background: var(--bg-subtle); }
.fams button.on { background: var(--accent-soft); color: var(--accent); font-weight: 500; }
.fams .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fams .ct { color: var(--text-muted); font-size: var(--fs-micro); flex: none; }

.toggle { display: flex; align-items: center; gap: var(--sp-2); font-size: var(--fs-small); cursor: pointer; }
.toggle input { accent-color: var(--accent); flex: none; }
.note { margin: var(--sp-2) 0 0; font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.6; }
</style>
