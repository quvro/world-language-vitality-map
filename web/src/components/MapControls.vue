<script setup lang="ts">
/**
 * 地图视图的那排控件（着色依据 / 尺寸尺度 / 活力层 / 只看选中）。
 *
 * 为什么从 WorldMap 里挪出来：用户要求"附着在选项卡上"。
 * 控件原来在卡片头部里，挪到选项卡那一行必须跨组件，
 * 而它读的是同一个 store，所以抽成独立组件最省事，也不用把文案和样式复制两份。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'

const store = useDataset()

const T = {
  zh: {
    byMacro: '按语区', byTrend: '按趋势',
    sizeRel: '相对自身峰值', sizeAbs: '跨语言比较',
    vitalityLayer: '活力层',
    onlySelected: '只看选中',
    onlySelectedHint: '先选一门语言；选中后此项只显示它',
  },
  en: {
    byMacro: 'By area', byTrend: 'By trend',
    sizeRel: 'vs own peak', sizeAbs: 'across langs',
    vitalityLayer: 'Vitality',
    onlySelected: 'Selected only',
    onlySelectedHint: 'Select a language first; this then shows only it',
  },
} as const
const t = computed(() => T[store.lang === 'zh' ? 'zh' : 'en'])
</script>

<template>
  <div class="ctrls">
    <div class="seg">
      <button :class="{ on: store.colorBy === 'macroarea' }"
              @click="store.colorBy = 'macroarea'">{{ t.byMacro }}</button>
      <button :class="{ on: store.colorBy === 'trend' }"
              @click="store.colorBy = 'trend'">{{ t.byTrend }}</button>
    </div>
    <div class="seg">
      <button :class="{ on: store.sizeMode === 'relative' }"
              @click="store.sizeMode = 'relative'">{{ t.sizeRel }}</button>
      <button :class="{ on: store.sizeMode === 'absolute' }"
              @click="store.sizeMode = 'absolute'">{{ t.sizeAbs }}</button>
    </div>
    <label class="chk">
      <input v-model="store.showVitality" type="checkbox">
      <span>{{ t.vitalityLayer }}</span>
    </label>
    <!-- 不设 disabled：禁用会让用户以为按钮坏了（实测反馈过） -->
    <label class="chk" :title="store.selected ? '' : t.onlySelectedHint">
      <input v-model="store.hideUnselected" type="checkbox">
      <span>{{ t.onlySelected }}</span>
    </label>
  </div>
</template>

<style scoped>
.ctrls { display: flex; align-items: center; gap: 6px; }
.seg { display: flex; border: 1px solid var(--border); border-radius: var(--radius-pill); overflow: hidden; }
.seg button {
  border: 0; background: transparent; cursor: pointer; font-family: inherit;
  padding: 3px 10px; font-size: var(--fs-micro); color: var(--text-secondary);
  white-space: nowrap;
}
.seg button.on { background: var(--accent); color: var(--text-inverse); }
.chk {
  display: flex; align-items: center; gap: 4px; cursor: pointer;
  font-size: var(--fs-micro); color: var(--text-secondary); white-space: nowrap;
}
.chk input { margin: 0; accent-color: var(--accent); }
</style>
