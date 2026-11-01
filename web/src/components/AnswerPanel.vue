<script setup lang="ts">
/**
 * 自然语言回答面板 —— 独立右侧抽屉。
 *
 * 为什么单独开一块而不是塞回输入框下面：答案里既有结论、又有数字、还有口径说明，
 * 挤在一条细栏里读不清。抽屉可以关掉，也不遮挡地图。
 *
 * 数据流向（顺序很重要）：
 *   问题 → 意图解析 → 写入 store（视图联动）→ **从 store.filtered 检索** → 组织答案
 * 所以答案里的数字与视图里的数字是同一个来源；大模型只负责把证据说成人话。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'

const store = useDataset()

const T = {
  zh: {
    title: '回答', close: '关闭',
    question: '你的问题',
    understood: '理解到的条件', noFilter: '没有具体条件（全部语言）',
    hit: '命中', of: '/', langs: '门语言',
    sourceLlm: '大模型措辞', sourceLocal: '本地规则合成',
    noKey: '未配置大模型密钥：下面的答案由本地模板根据真实数据合成，数字同样准确。',
    evidence: '数字来自哪里',
    evNote: (n: string) => `全部统计取自当前命中的数据（${n} 门），与地图、图表用的是同一份结果。`,
    busy: '正在检索数据…',
    more: '继续追问',
  },
  en: {
    title: 'Answer', close: 'Close',
    question: 'Your question',
    understood: 'Understood as', noFilter: 'no specific condition (all languages)',
    hit: 'Matched', of: '/', langs: 'languages',
    sourceLlm: 'wording by LLM', sourceLocal: 'composed locally',
    noKey: 'No API key: the answer below is composed locally from the real data — the numbers are equally exact.',
    evidence: 'Where the numbers come from',
    evNote: (n: string) => `All statistics come from the current ${n} matching languages — the same result the map and charts use.`,
    busy: 'Searching…',
    more: 'Ask again',
  },
} as const
const t = computed(() => T[store.lang === 'zh' ? 'zh' : 'en'])

/** 把 **加粗** 转成 HTML（内容是我们自己生成的，先转义再替换） */
function rich(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
}

/** 意图在 store 里是 Record<string, unknown>，这里收窄成实际用到的字段 */
interface AnsIntent {
  macroAreas?: string[]
  families?: string[]
  endangermentLevels?: number[]
  wikiOnly?: boolean
  growthMin?: number | null
  growthMax?: number | null
  minFeatures?: number | null
  featureId?: string
  featureValue?: string
}

const a = computed(() => store.nlAnswer)
const ev = computed(() => a.value?.evidence ?? null)

const chips = computed(() => {
  const it = (a.value?.intent ?? null) as AnsIntent | null
  if (!it) return []
  const out: string[] = []
  if (it.macroAreas?.length) out.push(it.macroAreas.join('、'))
  if (it.families?.length) out.push(it.families.join('、'))
  if (it.endangermentLevels?.length) out.push(`濒危 ${it.endangermentLevels.join('/')}`)
  if (it.wikiOnly) out.push('有维基版本')
  if (it.growthMin != null) out.push(`增长 ≥ ${(it.growthMin * 100).toFixed(0)}%`)
  if (it.growthMax != null) out.push(`增长 ≤ ${(it.growthMax * 100).toFixed(0)}%`)
  if (it.minFeatures != null) out.push(`特征 ≥ ${it.minFeatures}`)
  if (it.featureId) {
    out.push(it.featureValue ? `${it.featureId} = ${it.featureValue}` : it.featureId)
  }
  return out
})

/** 濒危等级分布的小条：宽度按占命中的比例 */
const levels = computed(() => {
  const e = ev.value
  if (!e?.levels?.length) return []
  const max = Math.max(...e.levels.map((x: any) => x.n))
  return e.levels.map((x: any) => ({
    lv: x.lv, n: x.n, w: max ? (x.n / max) * 100 : 0,
  }))
})
</script>

<template>
  <transition name="drawer">
    <aside v-if="a" class="answer">
      <header>
        <div class="hd">
          <span class="tag">{{ t.title }}</span>
          <span class="src">{{ a.source === 'llm' ? t.sourceLlm : t.sourceLocal }}</span>
        </div>
        <button class="x" :title="t.close" @click="store.closeNlAnswer()">×</button>
      </header>

      <p class="q">{{ a.question }}</p>

      <div class="chips">
        <span v-if="!chips.length" class="chip none">{{ t.noFilter }}</span>
        <span v-for="c in chips" :key="c" class="chip">{{ c }}</span>
      </div>

      <div class="hit">
        <b class="num">{{ a.evidence.count.toLocaleString('en-US') }}</b>
        <span class="of">{{ t.of }} {{ a.evidence.total.toLocaleString('en-US') }}</span>
        <span class="lab">{{ t.langs }}</span>
      </div>

      <h3>{{ a.answer.title }}</h3>
      <p class="lead" v-html="rich(a.answer.lead)" />

      <ul v-if="a.answer.bullets.length" class="bullets">
        <li v-for="(b, i) in a.answer.bullets" :key="i" v-html="rich(b)" />
      </ul>

      <div v-if="levels.length" class="levels">
        <div v-for="l in levels" :key="l.lv" class="lvrow">
          <span class="lvl">{{ l.lv }}</span>
          <span class="lvtrack"><i :style="{ width: l.w + '%' }" /></span>
          <span class="lvn num">{{ l.n }}</span>
        </div>
      </div>

      <ul v-if="a.answer.caveats.length" class="caveats">
        <li v-for="(c, i) in a.answer.caveats" :key="i">{{ c }}</li>
      </ul>

      <p v-if="a.note" class="note">{{ a.note }}</p>

      <div class="prov">
        <p class="provh">{{ t.evidence }}</p>
        <p class="provn">{{ t.evNote(a.evidence.count.toLocaleString('en-US')) }}</p>
        <p v-if="a.model" class="provm num">{{ a.model }}</p>
      </div>

      <button class="again" @click="store.closeNlAnswer()">{{ t.more }}</button>
    </aside>
  </transition>
</template>

<style scoped>
.answer {
  position: fixed; top: 0; right: 0; bottom: 0; z-index: 40;
  width: min(468px, 92vw);
  background: var(--bg-surface);
  border-left: 1px solid var(--border);
  box-shadow: -12px 0 40px rgba(35, 32, 28, 0.13);
  padding: var(--sp-5) var(--sp-5) var(--sp-6);
  overflow-y: auto;
  display: flex; flex-direction: column;
}
header { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); }
.hd { display: flex; align-items: baseline; gap: 9px; }
.tag {
  font-size: var(--fs-micro); font-weight: 700; letter-spacing: .08em;
  color: var(--accent); text-transform: uppercase;
}
.src { font-size: var(--fs-micro); color: var(--text-muted); }
.x {
  border: 0; background: transparent; color: var(--text-muted); cursor: pointer;
  font-size: 22px; line-height: 1; padding: 0 4px;
}
.x:hover { color: var(--accent); }

.q {
  margin: var(--sp-3) 0 0; font-size: var(--fs-small); color: var(--text-secondary);
  line-height: 1.6; padding-left: 10px; border-left: 2px solid var(--border-strong);
}
.chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: var(--sp-3); }
.chip {
  font-size: var(--fs-micro); padding: 2px 9px; border-radius: 20px;
  background: var(--bg-subtle); color: var(--text-secondary);
}
.chip.none { color: var(--text-muted); }

.hit {
  display: flex; align-items: baseline; gap: 7px;
  margin: var(--sp-4) 0 var(--sp-2);
  padding-bottom: var(--sp-3); border-bottom: 1px solid var(--border);
}
.hit b { font-size: 40px; font-weight: 700; color: var(--accent); line-height: 1; }
.hit .of { font-size: 15px; color: var(--text-muted); }
.hit .lab { font-size: var(--fs-micro); color: var(--text-muted); margin-left: auto; }

h3 { margin: var(--sp-3) 0 0; font-size: 1rem; font-weight: 700; }
.lead { margin: 6px 0 0; font-size: var(--fs-small); color: var(--text-secondary); line-height: 1.75; }
:deep(.lead strong), .bullets :deep(strong) { color: var(--text-primary); font-weight: 600; }

.bullets { margin: var(--sp-3) 0 0; padding: 0; list-style: none; }
.bullets li {
  position: relative; padding-left: 15px; margin-bottom: 7px;
  font-size: var(--fs-small); color: var(--text-secondary); line-height: 1.7;
}
.bullets li::before {
  content: ""; position: absolute; left: 3px; top: 9px;
  width: 4px; height: 4px; border-radius: 50%; background: var(--border-strong);
}

.levels { margin: var(--sp-3) 0 0; }
.lvrow { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.lvl {
  flex: none; width: 14px; text-align: right;
  font-size: 10.5px; color: var(--text-muted); font-family: Consolas, monospace;
}
.lvtrack { flex: 1; height: 7px; border-radius: 4px; background: var(--bg-subtle); overflow: hidden; }
.lvtrack i { display: block; height: 100%; background: var(--accent); opacity: .55; border-radius: 4px; }
.lvn { flex: none; width: 34px; text-align: right; font-size: 10.5px; color: var(--text-muted); }

.caveats { margin: var(--sp-4) 0 0; padding: 0; list-style: none; }
.caveats li {
  font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.7;
  margin-bottom: 5px;
}
.note {
  margin: var(--sp-3) 0 0; padding: 9px 11px;
  background: var(--bg-canvas); border-radius: var(--radius-md);
  font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.65;
}

.prov { margin-top: auto; padding-top: var(--sp-4); }
.provh {
  margin: 0; font-size: 10px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--text-muted);
}
.provn { margin: 4px 0 0; font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.6; }
.provm { margin: 3px 0 0; font-size: 10px; color: var(--border-strong); }

.again {
  margin-top: var(--sp-3); padding: 7px 12px; cursor: pointer;
  border: 1px solid var(--border-strong); border-radius: var(--radius-md);
  background: var(--bg-surface); color: var(--text-secondary);
  font-family: inherit; font-size: var(--fs-small);
}
.again:hover { background: var(--bg-subtle); }

.drawer-enter-active, .drawer-leave-active {
  transition: transform 240ms cubic-bezier(.22,.61,.36,1);
}
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }
</style>
