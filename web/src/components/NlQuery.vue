<script setup lang="ts">
/**
 * 自然语言查询条。
 *
 * 闭环：自然语言 → 结构化意图 → 写入 store → 全部视图联动 → 基于**真实数据**
 * 生成一句话解释。
 *
 * 两条解析通路：
 *   1. 大模型（POST /api/nl，密钥在服务端）—— 理解力强
 *   2. 本地规则解析器 —— 没配密钥或调用失败时兜底，功能不中断
 *
 * 刻意的职责划分：**模型只负责把话翻译成筛选条件，不负责算数**。
 * 解释里的统计数字一律在前端根据实际筛选结果算出来，
 * 所以它和视图里的数字必然一致，不会出现「模型编了个数」的情况。
 */
import { computed, ref } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { describeIntent, emptyHint, parseLocal } from '../../shared/intent.js'

const store = useDataset()
const { feature: featureLabel } = useDisplayNames()

const T = {
  zh: {
    placeholder: '用一句话提问，例如「非洲语区里语序是 SOV 且在增长的语言」',
    ask: '查询', busy: '解析中…', clear: '清除条件',
    srcLlm: '大模型解析', srcLocal: '本地规则解析',
    noKey: '未配置大模型密钥，已用本地规则解析',
    failed: '大模型调用失败，已退回本地规则解析',
    understood: '理解到的条件', none: '没有识别出具体条件',
    examples: '示例',
    result: (n: string) => `命中 ${n} 门语言`,
    withWiki: (n: string) => `其中 ${n} 门有维基百科版本`,
    median: (v: string) => `十年增长中位数 ${v}`,
  },
  en: {
    placeholder: 'Ask in one sentence, e.g. “SOV languages in Africa that are growing”',
    ask: 'Ask', busy: 'Parsing…', clear: 'Clear',
    srcLlm: 'parsed by LLM', srcLocal: 'parsed locally',
    noKey: 'No API key configured — parsed with local rules',
    failed: 'LLM call failed — fell back to local rules',
    understood: 'Understood as', none: 'no concrete condition recognised',
    examples: 'Examples',
    result: (n: string) => `${n} languages match`,
    withWiki: (n: string) => `${n} of them have a Wikipedia edition`,
    median: (v: string) => `median ten-year growth ${v}`,
  },
} as const
const t = computed(() => T[store.lang])

const question = ref('')
const busy = ref(false)
const chips = ref<{ key: string; label: string; value: string }[]>([])
const sourceText = ref('')
const explanation = ref('')
const hasResult = ref(false)

const EXAMPLES = {
  zh: [
    '非洲语区里语序是 SOV 且在增长的语言',
    '印欧语系中有声调的语言',
    '有维基百科版本、数据完整、这十年在衰退的语言',
    '定位到 2018 年',
  ],
  en: [
    'SOV languages in Africa that are growing',
    'Indo-European languages with tone',
    'Languages with a Wikipedia edition and complete data that declined',
    'Jump to 2018',
  ],
}

function ctx() {
  const features = (store.features?.features ?? []).slice(0, 80).map((f) => `${f.ID} ${f.Name}`)
  return {
    families: store.familyList.map((f) => f.family),
    features,
  }
}

/** 基于**真实筛选结果**生成解释，数字与视图一致 */
function summarize(): string {
  const rows = store.filtered
  if (!rows.length) return emptyHint(null, store.lang)
  const withWiki = rows.filter((l) => l.wiki_code).length
  const growths = rows
    .filter((l) => l.baseline_ok && l.growth != null)
    .map((l) => l.growth! * 100)
    .sort((a, b) => a - b)
  const parts = [
    t.value.result(rows.length.toLocaleString('en-US')),
    t.value.withWiki(withWiki.toLocaleString('en-US')),
  ]
  if (growths.length >= 3) {
    const med = growths[Math.floor(growths.length / 2)]
    parts.push(t.value.median(`${med >= 0 ? '+' : ''}${med.toFixed(0)}%`))
  }
  return parts.join(' · ')
}

async function submit() {
  const q = question.value.trim()
  if (!q || busy.value) return
  busy.value = true
  chips.value = []
  explanation.value = ''
  sourceText.value = ''

  let intent: Record<string, unknown> | null = null
  try {
    const res = await fetch('/api/nl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, context: ctx() }),
    })
    const data = await res.json()
    if (data?.ok && data.intent) {
      intent = data.intent
      sourceText.value = t.value.srcLlm
      explanation.value = String((data.intent as any).explanation ?? '')
    } else {
      intent = parseLocal(q, ctx())
      sourceText.value = data?.reason === 'no-key' ? t.value.noKey : t.value.failed
    }
  } catch {
    intent = parseLocal(q, ctx())
    sourceText.value = t.value.failed
  }

  store.applyIntent(intent)
  chips.value = describeIntent(intent, store.lang, (id) =>
    featureLabel(id, store.features?.features.find((f) => f.ID === id)?.Name ?? id))
  if (!explanation.value) explanation.value = summarize()
  else explanation.value = `${explanation.value} · ${summarize()}`
  hasResult.value = true
  busy.value = false
}

function reset() {
  question.value = ''
  chips.value = []
  explanation.value = ''
  sourceText.value = ''
  hasResult.value = false
  store.clearFilters()
}

function useExample(ex: string) {
  question.value = ex
  submit()
}
</script>

<template>
  <div class="nl">
    <div class="row">
      <span class="ico" aria-hidden="true">💬</span>
      <input
        v-model="question"
        type="text"
        :placeholder="t.placeholder"
        :disabled="busy"
        @keydown.enter="submit"
      >
      <button class="go" :disabled="busy || !question.trim()" @click="submit">
        {{ busy ? t.busy : t.ask }}
      </button>
      <button v-if="hasResult" class="clr" @click="reset">{{ t.clear }}</button>
    </div>

    <!-- 空态给可点的示例，降低"不知道该问什么"的门槛 -->
    <div v-if="!hasResult" class="examples">
      <span class="lab">{{ t.examples }}</span>
      <button v-for="ex in EXAMPLES[store.lang]" :key="ex" @click="useExample(ex)">{{ ex }}</button>
    </div>

    <div v-else class="result">
      <div class="understood">
        <span class="lab">{{ t.understood }}</span>
        <span v-if="!chips.length" class="none">{{ t.none }}</span>
        <span v-for="c in chips" :key="c.key" class="chip">
          <em>{{ c.label }}</em>{{ c.value }}
        </span>
        <span v-if="sourceText" class="src">{{ sourceText }}</span>
      </div>
      <p class="explain">{{ explanation }}</p>
    </div>
  </div>
</template>

<style scoped>
.nl {
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  padding: var(--sp-2) var(--sp-5) var(--sp-3);
}
.row { display: flex; align-items: center; gap: var(--sp-3); }
.ico { font-size: 14px; opacity: 0.7; flex: none; }
.row input {
  flex: 1; min-width: 0; padding: 7px 11px;
  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-canvas); color: var(--text-primary);
  font-family: inherit; font-size: var(--fs-small);
}
.row input:focus { outline: 2px solid var(--focus-ring); outline-offset: 1px; }
.row input:disabled { opacity: 0.6; }
.go {
  flex: none; padding: 7px 18px; cursor: pointer;
  border: 1px solid var(--accent); border-radius: var(--radius-md);
  background: var(--accent); color: var(--text-inverse);
  font-family: inherit; font-size: var(--fs-small); font-weight: 500;
  transition: opacity var(--dur-fast) var(--ease-out);
}
.go:disabled { opacity: 0.4; cursor: not-allowed; }
.clr {
  flex: none; padding: 7px 12px; cursor: pointer;
  border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-surface); color: var(--text-secondary);
  font-family: inherit; font-size: var(--fs-small);
}
.clr:hover { background: var(--bg-subtle); }

.examples, .understood {
  display: flex; flex-wrap: wrap; align-items: center;
  gap: var(--sp-1) var(--sp-2); margin-top: var(--sp-2);
  font-size: var(--fs-micro);
}
.lab { color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.examples button {
  border: 1px dashed var(--border-strong); border-radius: var(--radius-pill);
  background: transparent; color: var(--text-secondary); cursor: pointer;
  padding: 2px 10px; font-family: inherit; font-size: var(--fs-micro);
  transition: background var(--dur-fast) var(--ease-out);
}
.examples button:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.result { margin-top: var(--sp-2); }
.chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 10px; border-radius: var(--radius-pill);
  background: var(--accent-soft); color: var(--accent);
  font-size: var(--fs-micro);
}
.chip em { font-style: normal; color: var(--text-secondary); }
.none { color: var(--text-muted); }
.src { margin-left: auto; color: var(--text-muted); }
.explain {
  margin: var(--sp-1) 0 0; font-size: var(--fs-small);
  color: var(--text-primary); line-height: 1.5;
}
</style>
