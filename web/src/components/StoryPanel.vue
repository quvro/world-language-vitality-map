<script setup lang="ts">
/**
 * 故事模式面板 —— 替换左侧筛选面板（设计文档 §6：
 * 「故事模式时，左侧筛选面板折叠，改为引导文案 + 下一步按钮」）。
 *
 * 每步的正文里嵌的数字都是**实时从当前数据算出来的**（见 story.ts 的注释），
 * 所以数据更新后这些话不会变成假话。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'
import { STORY, storyFacts } from '@/story'

const store = useDataset()

const T = {
  zh: {
    step: (i: number, n: number) => `第 ${i} / ${n} 步`,
    prev: '上一步', next: '下一步', exit: '退出故事，自由探索',
    done: '故事结束', restart: '从头再看',
    exploreHint: '故事模式下也可以直接拖时间轴、点地图上的点',
  },
  en: {
    step: (i: number, n: number) => `Step ${i} of ${n}`,
    prev: 'Back', next: 'Next', exit: 'Exit story, explore freely',
    done: 'End of story', restart: 'Start over',
    exploreHint: 'You can still drag the timeline and click dots while in story mode',
  },
} as const
const t = computed(() => T[store.lang])

const facts = computed(() => storyFacts(store))
const idx = computed(() => store.storyStep ?? 0)
const step = computed(() => STORY[idx.value])
const lang = computed(() => (store.lang === 'zh' ? 'zh' : 'en') as 'zh' | 'en')

const title = computed(() => step.value?.[lang.value].title ?? '')
const body = computed(() => step.value?.[lang.value].body(store, facts.value) ?? '')
const note = computed(() => step.value?.[lang.value].note ?? '')
const isLast = computed(() => idx.value >= STORY.length - 1)
/** 正文里用 `**粗体**` 标重点，这里转成 HTML（内容是我们自己写的，不涉及用户输入） */
const bodyHtml = computed(() =>
  body.value
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>'))
</script>

<template>
  <aside class="story">
    <div class="head">
      <span class="counter num">{{ t.step(idx + 1, STORY.length) }}</span>
      <div class="dots">
        <button
          v-for="(s, i) in STORY" :key="s.key"
          class="dot" :class="{ on: i === idx, past: i < idx }"
          :title="s[lang].title"
          @click="store.goStory(i)"
        />
      </div>
    </div>

    <h2>{{ title }}</h2>
    <p class="body" v-html="bodyHtml" />
    <p v-if="note" class="note">{{ note }}</p>

    <div class="nav">
      <button class="ghost" :disabled="idx === 0" @click="store.goStory(idx - 1)">
        ← {{ t.prev }}
      </button>
      <button v-if="!isLast" class="primary" @click="store.goStory(idx + 1)">
        {{ t.next }} →
      </button>
      <button v-else class="primary" @click="store.goStory(0)">
        ↻ {{ t.restart }}
      </button>
    </div>

    <button class="exit" @click="store.goStory(null)">{{ t.exit }}</button>
    <p class="hint">{{ t.exploreHint }}</p>
  </aside>
</template>

<style scoped>
.story {
  display: flex; flex-direction: column;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--sp-4);
  overflow: hidden auto;
  min-height: 0; height: 100%;
}
.head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); flex: none; }
.counter {
  font-size: var(--fs-micro); color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.08em;
}
.dots { display: flex; gap: 4px; }
.dot {
  width: 7px; height: 7px; padding: 0; border-radius: 50%;
  border: 1px solid var(--border-strong); background: transparent; cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out);
}
.dot:hover { border-color: var(--accent); }
.dot.past { background: var(--border-strong); border-color: var(--border-strong); }
.dot.on { background: var(--accent); border-color: var(--accent); transform: scale(1.35); }

h2 {
  margin: var(--sp-3) 0 var(--sp-2); font-size: 1.05rem;
  font-weight: 600; line-height: 1.35;
}
.body {
  margin: 0; font-size: var(--fs-small); line-height: 1.85;
  color: var(--text-secondary);
}
.body :deep(strong) { color: var(--text-primary); font-weight: 600; }
.note {
  margin: var(--sp-3) 0 0; padding: var(--sp-3);
  background: var(--bg-canvas); border-radius: var(--radius-md);
  font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.7;
}

.nav { display: flex; gap: var(--sp-2); margin-top: auto; padding-top: var(--sp-4); flex: none; }
.nav button {
  flex: 1; padding: 7px 10px; border-radius: var(--radius-md);
  font-family: inherit; font-size: var(--fs-small); cursor: pointer;
  transition: background var(--dur-fast) var(--ease-out);
}
.nav .primary {
  border: 1px solid var(--accent); background: var(--accent); color: var(--text-inverse);
}
.nav .primary:hover { background: var(--accent-hover); }
.nav .ghost {
  border: 1px solid var(--border-strong); background: var(--bg-surface); color: var(--text-secondary);
}
.nav .ghost:hover:not(:disabled) { background: var(--bg-subtle); }
.nav .ghost:disabled { opacity: 0.4; cursor: not-allowed; }

.exit {
  margin-top: var(--sp-2); flex: none;
  border: 0; background: transparent; color: var(--text-muted);
  font-family: inherit; font-size: var(--fs-micro); cursor: pointer;
  text-decoration: underline; padding: 4px;
}
.exit:hover { color: var(--accent); }
.hint { margin: var(--sp-2) 0 0; flex: none; font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.6; }
</style>
