"""生成「2,662 格 = 2,662 门语言」的单位图（unit chart），用于 PPT 开场冲击页。

为什么做这个：10.0% 这个数字读起来没什么感觉，但把它画成 2,662 个格子、
只有 267 个亮着，视觉冲击是数量级的。这是数据可视化里最古老也最有效的
手法之一（unit chart / waffle chart），比任何饼图都更能让「比例」变成「体感」。
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

L = json.load(open("data/processed/languages.json", encoding="utf-8"))
AES = json.load(open("data/processed/aes.json", encoding="utf-8"))
UNI = json.load(open("data/processed/endangerment.json", encoding="utf-8"))


def level(l):
    gc = l.get("glottocode") or ""
    iso = (l.get("iso639p3") or "").lower()
    return (AES["by_glottocode"].get(gc)
            or UNI["by_glottocode"].get(gc)
            or UNI["by_iso639p3"].get(iso) or 7)


rows = [(l, level(l)) for l in L]
# 只按濒危等级排序，**档内保持原序**。
# 之前档内把「有维基」的排前面，结果橙色连成整块，看起来像"橙色语言是聚集的"——
# 那是排序造成的假象，不是数据。保持原序后橙色自然散开，才看得出它有多稀疏。
rows.sort(key=lambda r: r[1])

COLS = 54
CELL = 13
GAP = 2.5
PITCH = CELL + GAP

LEVEL_TINT = {
    1: "#7C9A6A", 2: "#C9B458", 3: "#D9964A",
    4: "#CF6B3F", 5: "#B34A35", 6: "#7D3226", 7: "#C9C3B6",
}
ACCENT = "#E4572E"

cells = []
for i, (l, lv) in enumerate(rows):
    col, row = i % COLS, i // COLS
    x, y = col * PITCH, row * PITCH
    if l.get("wiki_code"):
        fill = ACCENT
        style = f"background:{fill};"
    else:
        # 无维基：用濒危等级的颜色淡淡描一圈，主体近乎空白 ——
        # 让"空"本身也有信息，而不是一片灰
        style = (f"background:#F2EEE5;box-shadow:inset 0 0 0 1.3px {LEVEL_TINT[lv]}33;")
    cells.append(f'<i style="left:{x}px;top:{y}px;{style}"></i>')

n_rows = (len(rows) + COLS - 1) // COLS
grid_w, grid_h = COLS * PITCH - GAP, n_rows * PITCH - GAP

# 等级分带的标记位置
bands = []
seen = set()
for i, (l, lv) in enumerate(rows):
    if lv in seen:
        continue
    seen.add(lv)
    y = (i // COLS) * PITCH
    bands.append((lv, y))

total = len(rows)
has_wiki = sum(1 for l, _ in rows if l.get("wiki_code"))

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1600px;height:1000px;background:#FAF8F4;color:#23201C;
 font-family:"Microsoft YaHei","PingFang SC",sans-serif;padding:46px 52px;
 display:flex;gap:44px}}
.left{{flex:none;width:{grid_w + 92}px}}
.right{{flex:1;display:flex;flex-direction:column;justify-content:center}}
h1{{font-size:29px;font-weight:600;letter-spacing:.01em}}
.sub{{font-size:14px;color:#948C7E;margin-top:8px;line-height:1.6}}
.gridwrap{{position:relative;margin-top:26px;margin-left:92px}}
.grid{{position:relative;width:{grid_w}px;height:{grid_h}px}}
.grid i{{position:absolute;width:{CELL}px;height:{CELL}px;border-radius:2.5px;display:block}}
.band{{position:absolute;left:-92px;width:78px;text-align:right;
 font-size:11px;color:#948C7E;line-height:1.15;transform:translateY(-4px)}}
.band b{{display:block;color:#5C564C;font-weight:600;font-size:11.5px}}
.legend{{margin-top:20px;margin-left:92px;display:flex;align-items:center;gap:22px;
 font-size:12.5px;color:#5C564C}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:2.5px;
 margin-right:7px;vertical-align:-2px}}
.big{{font-size:78px;font-weight:700;color:{ACCENT};line-height:1;letter-spacing:-.02em}}
.bigl{{font-size:14px;color:#5C564C;margin-top:6px}}
.of{{font-size:26px;color:#C9C3B6;font-weight:600;margin-left:6px}}
.divider{{height:1px;background:#E7E1D5;margin:26px 0}}
.line{{font-size:15px;color:#23201C;line-height:1.75;font-weight:600}}
.note{{font-size:13.5px;color:#5C564C;line-height:1.8;margin-top:14px}}
.tag{{align-self:flex-start;display:inline-block;font-size:11px;padding:2px 9px;border-radius:20px;
 background:rgba(228,87,46,.1);color:{ACCENT};font-weight:600;margin-bottom:14px}}
</style></head><body>
<div class="left">
  <h1>2,662 个格子，一门语言一格</h1>
  <div class="sub">按语言学上的濒危等级排序：最上面是最健康的语言，最下面是已灭绝的</div>
  <div class="gridwrap">
    <div class="grid">{''.join(cells)}</div>
    {''.join(f'<div class="band" style="top:{y + 4}px"><b>{lab}</b>{sub}</div>'
             for lv, y in bands
             for lab, sub in [(
                 {1: "未濒危", 2: "受威胁", 3: "转移中", 4: "垂危",
                  5: "几近灭绝", 6: "已灭绝", 7: "无数据"}[lv],
                 {1: "967 门", 2: "532 门", 3: "612 门", 4: "144 门",
                  5: "136 门", 6: "223 门", 7: "48 门"}[lv])])}
  </div>
  <div class="legend">
    <span><i style="background:{ACCENT}"></i>有维基百科版本</span>
    <span><i style="background:#F2EEE5;box-shadow:inset 0 0 0 1.3px #C9C3B6"></i>没有</span>
    <span style="color:#948C7E">格子越往下，语言学上越接近消失</span>
  </div>
</div>
<div class="right">
  <span class="tag">本项目最想让你记住的一张图</span>
  <div class="big">{has_wiki}<span class="of">/ {total:,}</span></div>
  <div class="bigl">门语言拥有维基百科版本 —— <b>10.0%</b></div>
  <div class="divider"></div>
  <div class="line">橙色稀疏地散在最上面，越往下越少，最下面几乎一片空白。</div>
  <div class="note">最下面已灭绝的 223 门里，只有 2 门是橙色的。<br>
  而最上面「未濒危」的 967 门里，也仍有八成以上是空的 —— <br>
  所以这不是「快死的语言才没有数字入口」，<br>而是整个生态的共同处境。</div>
</div>
</body></html>"""

open("paper/figs/_unitgrid.html", "w", encoding="utf-8").write(html)
print(f"  已生成 HTML：{total} 格，{COLS} 列 × {n_rows} 行，"
      f"网格 {grid_w}x{grid_h}px，有维基 {has_wiki} 格")
