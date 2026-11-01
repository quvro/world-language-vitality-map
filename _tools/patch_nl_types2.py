"""回答面板与调用处的类型收窄。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- AnswerPanel：给 intent 一个明确形状
P = "web/src/components/AnswerPanel.vue"
s = io.open(P, encoding="utf-8").read()
OLD = """const a = computed(() => store.nlAnswer)
const ev = computed(() => a.value?.evidence ?? null)

const chips = computed(() => {
  const it = a.value?.intent
  if (!it) return []"""
NEW = """/** 意图在 store 里是 Record<string, unknown>，这里收窄成实际用到的字段 */
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
  if (!it) return []"""
if OLD in s:
    s = s.replace(OLD, NEW, 1)
    io.open(P, "w", encoding="utf-8").write(s)
    print("  ok   AnswerPanel intent 已收窄")
else:
    print("  MISS AnswerPanel 片段")

# ---- NlQuery：label 参数用 Language 类型
P2 = "web/src/components/NlQuery.vue"
s2 = io.open(P2, encoding="utf-8").read()
old = "    label: (r: { wals_id: string }) => langLabel(r),"
new = "    label: (r: Language) => langLabel(r),"
if old in s2:
    s2 = s2.replace(old, new, 1)
    if "import type { Language }" not in s2:
        s2 = s2.replace(
            "import { useDataset } from '@/stores/dataset'",
            "import { useDataset } from '@/stores/dataset'\nimport type { Language } from '@/types'",
            1,
        )
    io.open(P2, "w", encoding="utf-8").write(s2)
    print("  ok   NlQuery label 用 Language 类型")
else:
    print("  MISS NlQuery label 行")
