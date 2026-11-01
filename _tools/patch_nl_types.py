"""补两处类型：State 接口加 nlAnswer 字段；NlQuery 的 label 参数加类型。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- store 接口
P = "web/src/stores/dataset.ts"
s = io.open(P, encoding="utf-8").read()
ANCHOR = "    ticks: boolean\n  }"
if ANCHOR in s and "nlAnswer: NlAnswer | null" not in s.split("export interface NlAnswer")[0]:
    s = s.replace(
        ANCHOR,
        "    ticks: boolean\n  }\n"
        "  /** 自然语言回答（NlQuery 写入 / AnswerPanel 渲染） */\n"
        "  nlAnswer: NlAnswer | null",
        1,
    )
    io.open(P, "w", encoding="utf-8").write(s)
    print("  ok   State 接口已加 nlAnswer")
else:
    print("  ?? 未改动，请检查")

# ---- NlQuery 参数类型
P2 = "web/src/components/NlQuery.vue"
s2 = io.open(P2, encoding="utf-8").read()
old = "    label: (r) => langLabel(r),"
new = "    label: (r: { wals_id: string }) => langLabel(r),"
if old in s2:
    s2 = s2.replace(old, new, 1)
    io.open(P2, "w", encoding="utf-8").write(s2)
    print("  ok   label 参数已标注类型")
else:
    print("  MISS label 行")
