"""让证据包**自带单位与标签**，避免模型把原始比值当成人话印出来。

实测模型会写出「增长率中位数为 1.3374」「均处于同一层级（lv=1）」——
不是模型笨，是我给的数据里只有裸数字和字段名。
修法不是改提示词去"提醒它换算"，而是**在数据里就把话说完整**：
带 Pct / Text 后缀的字段已经是格式化好的字符串。
"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/shared/answer.js"
s = io.open(P, encoding="utf-8").read()

# 1) 濒危等级的中文标签
if "LEVEL_ZH" not in s:
    s = s.replace(
        "const pct = (x) => `${(x * 100).toFixed(1)}%`",
        "const pct = (x) => `${(x * 100).toFixed(1)}%`\n"
        "/** AES 1–6 的中文名。放在这里而不是从 store 取，\n"
        " *  因为 buildEvidence 是纯函数、也可能在 Node 里被单独调用。 */\n"
        "const LEVEL_ZH = {\n"
        "  1: '未濒危', 2: '受威胁', 3: '转移中',\n"
        "  4: '垂危', 5: '几近灭绝', 6: '已灭绝',\n"
        "}",
        1,
    )
    print("  ok   已加 LEVEL_ZH")

# 2) levels 带 label
s = s.replace(
    "    levels: Object.entries(lvCount).sort((a, b) => a[0] - b[0])\n"
    "      .map(([lv, c]) => ({ lv: Number(lv), n: c })),",
    "    // label 是给人看的；model 会直接引用它，而不是吐出 'lv=1'\n"
    "    levels: Object.entries(lvCount).sort((a, b) => a[0] - b[0])\n"
    "      .map(([lv, c]) => ({\n"
    "        lv: Number(lv), label: LEVEL_ZH[lv] || String(lv), n: c,\n"
    "      })),",
    1,
)

# 3) growth 带 medianPct
s = s.replace(
    "    growth: {\n"
    "      n: growths.length,\n"
    "      median: median(growths),\n"
    "      up: growths.filter((g) => g > 0).length,\n"
    "      down: growths.filter((g) => g < 0).length,\n"
    "    },",
    "    growth: {\n"
    "      n: growths.length,\n"
    "      median: median(growths),\n"
    "      // 模型会把裸比值当成人话印出来（实测写成 \"中位数为 1.3374\"），\n"
    "      // 所以这里直接给一个格式化好的字符串\n"
    "      medianPct: median(growths) == null ? null\n"
    "        : `${median(growths) >= 0 ? '+' : ''}${pct(median(growths))}`,\n"
    "      up: growths.filter((g) => g > 0).length,\n"
    "      down: growths.filter((g) => g < 0).length,\n"
    "    },",
    1,
)

# 4) busiest 带 viewsText / growthPct
s = s.replace(
    "    busiest: byViews.slice(0, 3).map((r) => ({\n"
    "      name: label(r), views: Math.round(r.views_recent ?? 0),\n"
    "      growth: r.growth ?? null,\n"
    "    })),",
    "    busiest: byViews.slice(0, 3).map((r) => ({\n"
    "      name: label(r), views: Math.round(r.views_recent ?? 0),\n"
    "      viewsText: num(Math.round(r.views_recent ?? 0)),\n"
    "      growth: r.growth ?? null,\n"
    "      growthPct: r.growth == null ? null\n"
    "        : `${r.growth >= 0 ? '+' : ''}${pct(r.growth)}`,\n"
    "    })),",
    1,
)

io.open(P, "w", encoding="utf-8").write(s)
print("  ok   answer.js 已自带单位与标签")

# 5) 提示词里明确一句：带后缀的字段已是成品
P2 = "web/vite.config.ts"
t = io.open(P2, encoding="utf-8").read()
OLD = "'如果证据显示命中数为 0，就直说没有命中，并建议放宽哪个条件。',"
NEW = ("'如果证据显示命中数为 0，就直说没有命中，并建议放宽哪个条件。',\n"
       "              '证据里带 Pct / Text 后缀的字段**已经是格式化好的**（例如 medianPct=\"+133.7%\"、'\n"
       "              'viewsText=\"645,562\"），直接引用，不要再做任何换算；'\n"
       "              '带 label 的字段也直接引用 label，不要输出 lv 这类内部字段名。',")
if OLD in t:
    t = t.replace(OLD, NEW, 1)
    io.open(P2, "w", encoding="utf-8").write(t)
    print("  ok   提示词已补充字段约定")
else:
    print("  MISS 提示词片段")
