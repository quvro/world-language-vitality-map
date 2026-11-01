"""修章节页备注：让 divider() 自己接收备注文本，避免 prs.slides[-1] 取错页。"""

import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "_tools/build_ppt2.py"
s = io.open(P, encoding="utf-8").read()

# 1) divider 增加 nt 参数并在内部设置备注
s = s.replace(
    'def divider(no, zh, en, desc):\n'
    '    s = slide(no, en)',
    'def divider(no, zh, en, desc, nt=""):\n'
    '    s = slide(no, en)',
    1,
)
s = s.replace(
    '    rect(s, 0.72, 3.72, 0.95, 0.05, ACCENT)\n    return s',
    '    rect(s, 0.72, 3.72, 0.95, 0.05, ACCENT)\n'
    '    if nt:\n'
    '        note(s, nt)\n'
    '    return s',
    1,
)

# 2) 去掉原先「divider 之后单独调 note」的写法，改成把文本传进 divider
CALLS = [
    ('divider(3, "一、问题与意义", "01", "一条被忽略的流失，以及它为什么值得被看见")\n'
     'note(prs.slides[-1], "先看第一部分：问题本身。")',
     'divider(3, "一、问题与意义", "01", "一条被忽略的流失，以及它为什么值得被看见",\n'
     '        "先看第一部分：问题本身。")'),
    ('divider(8, "二、数据与系统", "02", "五个来源、15.7 万行数据、六个联动视图")\n'
     'note(prs.slides[-1], "第二部分：数据是怎么来的，系统是怎么搭的。")',
     'divider(8, "二、数据与系统", "02", "五个来源、15.7 万行数据、六个联动视图",\n'
     '        "第二部分：数据是怎么来的，系统怎么搭的。")'),
    ('divider(12, "三、四个创新点", "03", "两个表现手法上的，两个方法论上的")\n'
     'note(prs.slides[-1], "第三部分，也是我最想讲的部分：四个创新点。")',
     'divider(12, "三、四个创新点", "03", "两个表现手法上的，两个方法论上的",\n'
     '        "第三部分，也是我最想讲的部分：四个创新点。")'),
    ('divider(17, "四、规律与结论", "04", "四条发现、三条局限、三个后续方向")\n'
     'note(prs.slides[-1], "最后一部分，是我从数据里读出来的规律。")',
     'divider(17, "四、规律与结论", "04", "四条发现、三条局限、三个后续方向",\n'
     '        "最后一部分，是我从数据里读出来的规律。")'),
]
hit = 0
for old, new in CALLS:
    if old in s:
        s = s.replace(old, new, 1)
        hit += 1
    else:
        print("  未匹配：", old.splitlines()[0][:46])

io.open(P, "w", encoding="utf-8").write(s)
print(f"  改写 {hit}/{len(CALLS)} 个章节页调用")
