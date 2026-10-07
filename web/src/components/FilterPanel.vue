<script setup lang="ts">
/** 左侧筛选面板。所有筛选都写进 store，由 store 驱动全部视图联动。 */
import { computed, ref } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { MACRO_AREAS, type MacroArea } from '@/types'
import { categoryPalette } from '@/theme/echarts-theme.js'

const store = useDataset()
const { macro: macroLabel, family: familyLabel } = useDisplayNames()
const PALETTE = categoryPalette()
const q = ref('')

const families = computed(() => {
  const s = q.value.trim().toLowerCase()
  const list = store.familyList
  return s ? list.filter((f) => f.family.toLowerCase().includes(s)) : list
})

const activeCount = computed(() =>
  store.macroAreas.length + store.families.length +
  (store.onlyReliable ? 1 : 0) + (store.search ? 1 : 0)
)
</script>

<template>
  <aside class="panel">
    <div class="head">
      <h2>筛选</h2>
      <button v-if="activeCount" class="clear" @click="store.clearFilters()">
        清空 {{ activeCount }}
      </button>
    </div>

    <label class="search">
      <input v-model="store.search" type="search" placeholder="搜索语言名…">
    </label>

    <section>
      <h3>语区 <span class="tip">点击筛选，可多选</span></h3>
      <div class="chips">
        <button
          v-for="(m, i) in MACRO_AREAS"
          :key="m"
          class="chip"
          :class="{ on: store.macroAreas.includes(m) }"
          :style="store.macroAreas.includes(m) ? { background: PALETTE[i], borderColor: PALETTE[i], color: '#fff' } : {}"
          @click="store.toggleMacroArea(m as MacroArea)"
        >
          <i :style="{ background: store.macroAreas.includes(m) ? '#fff' : PALETTE[i] }" />{{ macroLabel(m) }}
        </button>
      </div>
    </section>

    <section class="grow">
      <h3>语系 <span class="n">{{ store.familyList.length }}</span>
        <span class="tip">点击筛选，可多选</span>
      </h3>
      <input v-model="q" class="mini" type="search" placeholder="过滤语系…">
      <ul class="fams">
        <li v-for="f in families" :key="f.family">
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

    <section>
      <h3>数据可信度</h3>
      <label class="toggle">
        <input v-model="store.onlyReliable" type="checkbox">
        <span>只看基线可靠的语言</span>
      </label>
      <p class="note">
        部分小语种维基在早期几乎没有记录，后来才有流量。
        它们的"增长率"是统计伪影，勾选此项可排除。
      </p>
    </section>

    <div class="tally">
      <div class="row">
        <span>命中</span>
        <strong class="num">{{ store.filtered.length.toLocaleString('en-US') }}</strong>
        <span class="of">/ {{ store.langs.length.toLocaleString('en-US') }}</span>
      </div>
      <p v-if="store.hasFilter" class="tallynote">
        地图上未命中的点会<strong>淡出但保留</strong>作为地理参照；
        其余图表只显示命中的语言。
      </p>
      <p v-else class="tallynote">当前没有筛选，显示全部语言。</p>
    </div>
  </aside>
</template>

<style scoped>
.panel {
  display: flex; flex-direction: column; gap: var(--sp-4);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  overflow: hidden auto;
  min-height: 0;
}
.head { display: flex; align-items: baseline; justify-content: space-between; }
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
h3 {
  margin: 0 0 var(--sp-2); font-size: var(--fs-micro);
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--text-muted); font-weight: 600;
}
h3 .n { color: var(--text-muted); font-weight: 400; }
.clear {
  border: 0; background: transparent; color: var(--accent);
  font-size: var(--fs-small); cursor: pointer; font-family: inherit;
}
.clear:hover { text-decoration: underline; }

.search input, .mini {
  width: 100%; padding: 7px 11px;
  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-canvas); color: var(--text-primary);
  font-family: inherit; font-size: var(--fs-small);
}
.search input:focus, .mini:focus { outline: 2px solid var(--focus-ring); outline-offset: 1px; }
.mini { margin-bottom: var(--sp-2); }

.chips { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; font-size: var(--fs-small); font-family: inherit;
  border: 1px solid var(--border); border-radius: var(--radius-pill);
  background: var(--bg-surface); color: var(--text-secondary); cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out);
}
.chip:hover { background: var(--bg-subtle); }
.chip.on { background: var(--bg-subtle); font-weight: 500; }
.chip i { width: 7px; height: 7px; border-radius: 50%; }

.grow { display: flex; flex-direction: column; min-height: 0; flex: 1; }
.fams { list-style: none; margin: 0; padding: 0; overflow: auto; min-height: 90px; }
.fams button {
  display: flex; justify-content: space-between; gap: var(--sp-2);
  width: 100%; border: 0; background: transparent; cursor: pointer;
  padding: 4px 6px; border-radius: var(--radius-sm);
  font-family: inherit; font-size: var(--fs-small); color: var(--text-secondary);
  text-align: left;
}
.fams button:hover { background: var(--bg-subtle); }
.fams button.on { background: var(--accent-soft); color: var(--accent); font-weight: 500; }
.fams .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fams .ct { color: var(--text-muted); font-size: var(--fs-micro); }

.toggle { display: flex; align-items: center; gap: var(--sp-2); font-size: var(--fs-small); cursor: pointer; }
.toggle input { accent-color: var(--accent); }
.note { margin: var(--sp-2) 0 0; font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.6; }

.tally {
  margin-top: auto; padding-top: var(--sp-3);
  border-top: 1px solid var(--border);
  font-size: var(--fs-small); color: var(--text-secondary);
}
.tally strong { color: var(--accent); font-size: 1.05rem; }
</style>
