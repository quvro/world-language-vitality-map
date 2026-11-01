"""接入"检索 + 回答"：store 状态、NlQuery 调用、/api/nl/answer 端点、App 挂载面板。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def patch(path, pairs, label):
    s = io.open(path, encoding="utf-8").read()
    hit = 0
    for old, new in pairs:
        if old in s:
            s = s.replace(old, new, 1)
            hit += 1
        else:
            print(f"  [{label}] MISS {old.splitlines()[0][:56]}")
    io.open(path, "w", encoding="utf-8").write(s)
    print(f"  [{label}] {hit}/{len(pairs)}")


# ------------------------------------------------------------ store
patch("web/src/stores/dataset.ts", [
    (
        "    glyphChannels: { ring: true, arc: true, core: true, size: true, ticks: true },",
        """    glyphChannels: { ring: true, arc: true, core: true, size: true, ticks: true },
    /**
     * 自然语言回答。由 NlQuery 写入、AnswerPanel 渲染。
     *
     * 放在 store 而不是组件局部：面板是独立的浮层，和输入框不在同一个组件树里，
     * 用 store 传递最省事，也保证"答案"和"当前筛选"始终指向同一份数据。
     */
    nlAnswer: null as NlAnswer | null,""",
    ),
    (
        "    toggleComparison(id: string) {",
        """    closeNlAnswer() {
      this.nlAnswer = null
    },

    toggleComparison(id: string) {""",
    ),
], "store")

# 类型定义
s = io.open("web/src/stores/dataset.ts", encoding="utf-8").read()
if "export interface NlAnswer" not in s:
    anchor = "export interface Aes {"
    s = s.replace(anchor, '''/** 自然语言回答的结构（见 shared/answer.js） */
export interface NlAnswer {
  question: string
  source: 'llm' | 'local'
  intent: Record<string, unknown> | null
  evidence: {
    count: number
    total: number
    share: number
    withWiki: number
    wikiShare: number
    levels: { lv: number; n: number }[]
    areas: { name: string; n: number }[]
    families: { name: string; n: number }[]
    growth: { n: number; median: number | null; up: number; down: number }
    busiest: { name: string; views: number; growth: number | null }[]
    absent: { name: string; features: number }[]
  }
  answer: { title: string; lead: string; bullets: string[]; caveats: string[] }
  model: string | null
  note: string
}

export interface Aes {''', 1)
    io.open("web/src/stores/dataset.ts", "w", encoding="utf-8").write(s)
    print("  [store] 已加 NlAnswer 接口")

# ------------------------------------------------------------ NlQuery
patch("web/src/components/NlQuery.vue", [
    ("import { describeIntent, emptyHint, parseLocal } from '../../shared/intent.js'",
     "import { describeIntent, emptyHint, parseLocal } from '../../shared/intent.js'\n"
     "import { buildEvidence, composeAnswer } from '../../shared/answer.js'"),
    ("const { feature: featureLabel } = useDisplayNames()",
     "const { feature: featureLabel, language: langLabel } = useDisplayNames()"),
    (
        """  hasResult.value = true
  busy.value = false
}""",
        """  hasResult.value = true
  busy.value = false

  // 检索 + 回答（独立面板）
  void answerNow(q, intent)
}

/**
 * 第二段：**从当前命中的结果里检索事实**，再组织答案。
 *
 * 顺序刻意：先 applyIntent（视图已联动），再读 store.filtered ——
 * 保证答案里的数字就是地图上那一批。大模型只拿证据去措辞，不算数。
 */
async function answerNow(q: string, intent: Record<string, unknown> | null) {
  const evidence = buildEvidence({
    rows: store.filtered,
    total: store.langs.length,
    ebw: store.endangermentByWals,
    featCount: store.featureCount,
    label: (r) => langLabel(r),
  })
  const fromLlm = sourceText.value === t.value.srcLlm
  const local = composeAnswer({ question: q, intent, evidence, lang: store.lang })
  store.nlAnswer = {
    question: q,
    source: fromLlm ? 'llm' : 'local',
    intent,
    evidence,
    answer: local,
    model: null,
    note: fromLlm ? '' : t.value.localNote,
  }
  try {
    const res = await fetch('/api/nl/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, intent, evidence, lang: store.lang }),
    })
    const d = await res.json()
    if (d?.ok && d.answer?.title) {
      store.nlAnswer = {
        ...store.nlAnswer!, answer: d.answer, model: d.model ?? null,
        source: 'llm', note: '',
      }
    }
  } catch {
    // 失败就用本地合成答案，不打断用户
  }
}""",
    ),
    ("    median: (v: string) => `十年增长中位数 ${v}`,",
     "    median: (v: string) => `十年增长中位数 ${v}`,\n"
     "    localNote: '大模型未参与措辞：下面的答案由本地模板根据真实数据合成，数字同样准确。',"),
    ("    median: (v: string) => `median ten-year growth ${v}`,",
     "    median: (v: string) => `median ten-year growth ${v}`,\n"
     "    localNote: 'the LLM did not phrase this: the answer below was composed locally from the real data.',"),
], "NlQuery")

# ------------------------------------------------------------ App
patch("web/src/App.vue", [
    ("import StoryPanel from '@/components/StoryPanel.vue'",
     "import StoryPanel from '@/components/StoryPanel.vue'\n"
     "import AnswerPanel from '@/components/AnswerPanel.vue'"),
], "App")

s = io.open("web/src/App.vue", encoding="utf-8").read()
if "<AnswerPanel />" not in s:
    # 挂在最外层 div 的末尾（在 NlQuery 之后）
    idx = s.rfind("</template>")
    close = s.rfind("</div>", 0, idx)
    s = s[:close] + "  <AnswerPanel />\n  " + s[close:]
    io.open("web/src/App.vue", "w", encoding="utf-8").write(s)
    print("  [App] 已挂载 AnswerPanel")
