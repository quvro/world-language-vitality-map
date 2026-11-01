"""字形模式排版收尾：副标题缩成一行，开关面板挪到左下角（避开副标题）。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/components/WorldMap.vue"
s = io.open(P, encoding="utf-8").read()


def rep(old, new, tag):
    global s
    if old in s:
        s = s.replace(old, new, 1)
        print(f"  ok   {tag}")
    else:
        print(f"  MISS {tag}")


# 1) 面板移到左下角 —— 左上角会被副标题压住，左下（南太平洋）本来最空
rep(
    "  position: absolute; left: 16px; top: 96px; width: 246px; z-index: 6;",
    "  position: absolute; left: 16px; bottom: 56px; width: 246px; z-index: 6;",
    "面板位置",
)

# 2) 副标题缩成一行
rep(
    """    glyphSub: '一个符号 = 一门语言 · 环色 = 濒危等级 · 扇形 = 描写深度 · '
      + '实心点 = 有维基版本 · 大小 = 当月浏览量 · 刻度 = 其他维基项目',""",
    "    glyphSub: '一个符号 = 一门语言 · 环色=濒危 · 扇形=描写深度 · 实心=有维基 · 大小=浏览量',",
    "中文副标题",
)
rep(
    """    glyphSub: 'one symbol = one language · ring = endangerment · wedge = description depth '
      + '· filled dot = has Wikipedia · size = monthly views · ticks = other wiki projects',""",
    "    glyphSub: 'one symbol = one language · ring=endangerment · wedge=depth · "
    "filled=has Wikipedia · size=views',",
    "英文副标题",
)

io.open(P, "w", encoding="utf-8").write(s)
