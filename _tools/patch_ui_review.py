"""按用户红框意见集中改一轮。

A 字形面板太不显眼 → 强调色描边 + 更重阴影 + 更大字号
B 标签栏与地图割裂 → 去掉间隙、标签贴住卡片上沿
C 地图卡片头部太高 → 去掉追加的尺寸说明，标题保留但只占一行
D 去掉「先点一个点」提示
E 「只看基线可靠的」→「去除记录数据过少的语言」
F 去掉时间轴上的「折线 = …合计」说明
"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(p):
    return io.open(p, encoding="utf-8").read()


def save(p, s):
    io.open(p, "w", encoding="utf-8").write(s)


def sub(path, old, new, tag, count=1):
    s = load(path)
    if old in s:
        save(path, s.replace(old, new, count))
        print(f"  ok   {tag}")
        return True
    print(f"  MISS {tag}")
    return False


# ---------------------------------------------------------------- A 字形面板
sub("web/src/components/WorldMap.vue",
    """.channels {
  position: absolute; left: 16px; bottom: 56px; width: 246px; z-index: 6;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--border); border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 10px 12px 11px;
  backdrop-filter: blur(6px);
}""",
    """.channels {
  position: absolute; left: 16px; bottom: 56px; width: 268px; z-index: 6;
  background: rgba(255, 255, 255, 0.98);
  /* 用户反馈"太不明显"：改成强调色描边 + 左侧粗条 + 更重的投影，
     让它在地图上是一个明确的浮层，而不是一块半透明的白 */
  border: 1.5px solid var(--accent);
  border-left-width: 5px;
  border-radius: var(--radius-md);
  box-shadow: 0 10px 30px rgba(35, 32, 28, 0.17),
    0 0 0 5px rgba(228, 87, 46, 0.06);
  padding: 12px 13px 13px;
  backdrop-filter: blur(8px);
}""", "A 字形面板容器")

sub("web/src/components/WorldMap.vue",
    """.ch-head {
  margin: 0 0 8px; font-size: var(--fs-micro); font-weight: 600;
  color: var(--text-secondary); line-height: 1.5;
}""",
    """.ch-head {
  margin: 0 0 9px; font-size: var(--fs-small); font-weight: 700;
  color: var(--text-primary); line-height: 1.45;
  padding-bottom: 7px; border-bottom: 1px solid var(--border);
}""", "A 面板标题")

# 复选框与文字放大一号
sub("web/src/components/WorldMap.vue",
    "  flex: none; width: 13px; height: 13px; margin-top: 2px;",
    "  flex: none; width: 15px; height: 15px; margin-top: 2px;", "A 勾选框尺寸")
sub("web/src/components/WorldMap.vue",
    """.ch-txt b { font-size: var(--fs-micro); font-weight: 600; color: var(--text-secondary); }""",
    """.ch-txt b { font-size: var(--fs-small); font-weight: 600; color: var(--text-primary); }""",
    "A 通道名")

# ---------------------------------------------------------------- C 缩短头部
sub("web/src/components/WorldMap.vue",
    """        <p class="hint">
          {{ title.s }} ·
          <span class="sizetip">{{ store.sizeMode === 'relative' ? t.legendRelative : t.legendAbsolute }}</span>
        </p>""",
    """        <!-- 头部压缩成一行：尺寸说明挪进 title 提示，把高度让给地图 -->
        <p class="hint" :title="store.sizeMode === 'relative' ? t.legendRelative : t.legendAbsolute">
          {{ title.s }}
        </p>""", "C 头部压缩")

# ---------------------------------------------------------------- D 去掉提示
sub("web/src/components/WorldMap.vue",
    "          <em v-if=\"!store.selected\" class=\"why\">{{ t.pickFirst }}</em>\n",
    "", "D 去掉「先点一个点」")

# ---------------------------------------------------------------- E 语义替换
P = "web/src/components/FilterPanel.vue"
s = load(P)
n0 = s
s = s.replace("只看基线可靠的", "去除记录数据过少的语言")
# 描述改成与之相符的说法
s = re.sub(
    r"部分小语种维基在早期几乎没有记录[^'\"]*",
    "部分小语种维基在早期几乎没有记录，后来才有流量，算出来的增长率是统计伪影。"
    "勾选此项会把这些记录过少的语言整体剔除。",
    s,
)
if s != n0:
    save(P, s)
    print("  ok   E 筛选器文案")
else:
    print("  MISS E 筛选器文案")

# ---------------------------------------------------------------- F 时间轴
P2 = "web/src/components/VitalityTimeline.vue"
s2 = load(P2)
n2 = s2
s2 = s2.replace("折线 = 当前筛选范围内各语言浏览量的合计", "")
if s2 != n2:
    save(P2, s2)
    print("  ok   F 去掉时间轴说明")
else:
    print("  MISS F 时间轴说明")

# ---------------------------------------------------------------- B 标签相连
P3 = "web/src/App.vue"
s3 = load(P3)
if "标签栏与下方视图连成一体" not in s3:
    idx = s3.rfind("</style>")
    add = """
/* 标签栏与下方视图连成一体（用户反馈：两者看着是割裂的）。
   做法是去掉中间的间隙，并让标签压住卡片上沿 1px，
   视觉上标签就像长在卡片上的页签。 */
.col-center { gap: 0; }
.col-center .tabs { margin-bottom: -1px; position: relative; z-index: 2; }
.col-center .stage > .card { border-top-left-radius: 0; border-top-right-radius: 0; }
"""
    s3 = s3[:idx] + add + s3[idx:]
    save(P3, s3)
    print("  ok   B 标签与卡片相连")
else:
    print("  ok   B 已改过")
