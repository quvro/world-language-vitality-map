# 生图 Prompt：系统架构图 与 数据处理流程图

> 面向顶会论文（CHI / IEEE VIS / NeurIPS）的插图风格：**低饱和、细线、大留白、无装饰**。
> 严格禁用彩虹色 / 霓虹色 / 渐变 / 3D / 投影。

---

## 0. 两图共用的配色与字体（先定死，保证两张图是一套）

| 用途 | 名称 | Hex | 说明 |
|---|---|---|---|
| 数据源层 | 砖红 | `#B5564F` | 低饱和红，仅用于"输入" |
| 处理层 | 灰蓝 | `#4A6E8A` | 低饱和蓝，仅用于"处理" |
| 存储 / 契约 | 灰 | `#8C8880` | 中性灰，不参与语义 |
| 应用层 | 苔绿 | `#6E8B6B` | 低饱和绿，仅用于"输出" |
| 交互层 | 深灰 | `#5C574F` | 文字与边框 |
| 背景 | 米白 | `#FAF8F4` | 不用纯白，避免刺眼 |
| 边框线 | 浅灰 | `#D9D5CC` | 1px，全部统一 |
| 强调（极少量） | 砖红 | `#B5564F` | 一张图里最多出现 2 处 |

**字体**：Inter / Helvetica Neue / Arial，无衬线；层标题用 11pt 大写字母 + 0.08em 字距；节点标签 9–10pt；数字用等宽（JetBrains Mono / Roboto Mono）。

**共同约束（写进每条 prompt 末尾）**
```
Style constraints: flat vector, 1px hairline strokes, no gradients, no drop shadows,
no 3D, no bevels, no rainbow palette (only desaturated brick red, slate blue,
moss green and warm gray), no emoji, no clip-art, no decorative frames,
generous white space, left-aligned labels, publication figure quality, 300 dpi.
```

---

## 1. 系统架构图（替换 `01-mindmap.png`）

**信息结构**（严格按论文第二节）

```
① 数据来源层   5 个公开来源
     WALS CLDF（2,662 语言 × 192 特征 → 76,475 行）
     Wikimedia REST（135 个月 → 65,161 行）
     Glottolog CLDF（AES / 描写深度 / 文献数）
     Wikidata SPARQL（P1999 / P279 / ISO 639-1↔639-3）
     Wikimedia Sitematrix（374 个维基版本）

② 处理层       7 个幂等脚本 → 实体对齐 → SQLite 9 张表 / 157,736 行

③ 应用层       一份 JSON 契约 → Vue 3 + Pinia 状态仓库
     6 个视图：地图 / 活力变化 / 条件对比 / 记录缺口 / 濒危×关注 / 流向
     3 个功能：复合字形 / 语言体检单 / 大模型问答

④ 交互层       筛选联动 · 指向即解释 · 故事模式 · URL 状态分享 · 自然语言提问
```

**Prompt（可直接粘贴）**

```
A publication-quality system architecture diagram for an academic HCI/visualization paper.
Clean flat vector style, generous white space, 16:10 landscape, 3200px wide.

Layout: four horizontal bands stacked top to bottom, separated by thin 1px warm-gray rules
(#D9D5CC), each band with a small uppercase layer label at the far left in 11pt
letter-spaced sans-serif: "DATA SOURCES", "PIPELINE", "APPLICATION", "INTERACTION".

Band 1 — five equal rounded rectangles in one row, 6px corner radius, 1px stroke,
each with a desaturated brick-red tinted fill (#B5564F at 12% opacity) and a small
label plus a tiny monospace count underneath:
"WALS CLDF" 76,475 rows · "Wikimedia REST" 65,161 rows · "Glottolog CLDF" 3 sources ·
"Wikidata SPARQL" ISO alignment · "Sitematrix" 374 editions.

Band 2 — a single wide rounded rectangle centered, slate-blue tint (#4A6E8A at 14%),
labeled "7 idempotent scripts · entity alignment · SQLite, 9 tables / 157,736 rows".
Inside it, three small pill-shaped tags connected by thin lines to a small hub dot,
reading "WALS code", "Glottocode", "ISO 639-3" — indicating a three-way key mapping.
Five thin vertical arrows drop from band 1 into this rectangle.

Band 3 — one wide rectangle, moss-green tint (#6E8B6B at 12%), labeled
"JSON contract → Vue 3 + Pinia single store". Inside, two rows of small chips:
first row six chips "map", "growth", "compare", "gaps", "endangerment", "flow";
second row three chips "glyph", "check-up", "ask". A single thin arrow from band 2 into it.

Band 4 — a single row of four short text labels separated by thin vertical rules:
"linked filtering", "hover to explain", "story mode", "URL state / natural language".
One thin arrow down from band 3.

In the bottom-right corner, inset three small rectangular thumbnails of actual screenshots
(a world map with dots, a sparse data matrix, a sankey-like flow), each 1px framed,
aligned on one baseline, sized equally, occupying about 18% of the canvas width,
connected to band 3 by two thin lines.

Text is English, minimal, left-aligned. Numbers in monospace.
No rainbow colors. Only desaturated brick red, slate blue, moss green, warm gray.
Style constraints: flat vector, 1px hairline strokes, no gradients, no drop shadows,
no 3D, no bevels, no emoji, no clip-art, no decorative frames, generous white space,
publication figure quality, 300 dpi.
```

**中文版**：把上面所有引号内的英文标签替换为中文，并把最后一句改成
`图中文字全部使用简体中文，思源黑体`。**但请注意**：主流生图模型渲染中文长标签极易出错（缺笔画、错字），见文末建议。

---

## 2. 数据处理流程图（思维导图式，替换流程配图）

**信息结构**

```
根：5 个公开来源
 ├─ 抓取：7 个脚本（幂等，重跑一致）
 ├─ 清洗：实体对齐（WALS 码 ↔ Glottocode ↔ ISO 639-3）
 │        · 一个小语种可能被多个维基版本认领 → 取并集还是取主版本，需决策
 ├─ 聚合：月度序列（135 个月）→ 增长率 + 基线可靠性标记
 ├─ 建库：9 张表（2 张维表 + 3 张事实表 + 4 张辅助表）
 └─ 导出：一份 JSON 契约（0.9 MB / 2.2 MB / 4.9 MB 三个文件）
```

**Prompt（可直接粘贴）**

```
A publication-quality data pipeline mind map for an academic visualization paper.
Left-to-right tree layout, flat vector, generous white space, 16:10 landscape, 3200px wide.

Root node at far left: a rounded rectangle with a brick-red hairline stroke (#B5564F),
label "5 public sources", monospace sublabel "157,736 rows".

From the root, five thin arrows fan out to a vertical column of five small nodes,
each a plain text label with a tiny monospace count to its right:
"WALS CLDF — 76,475" · "Wikimedia REST — 65,161" · "Glottolog CLDF — 9,302" ·
"Wikidata SPARQL — 374" · "Sitematrix — 374".
Nodes have 1px hairline strokes in warm gray, no fills.

Each of the five nodes then connects with a thin elbow line into a central vertical
"processing spine" — a tall narrow rounded rectangle in slate blue (#4A6E8A at 12%).
The spine is divided into three stacked segments labeled from top to bottom:
"fetch · 7 idempotent scripts", "clean · entity alignment", "aggregate · monthly series".

To the right of the spine, an emphasis callout: a small slate-blue box with three
pill tags "WALS code", "Glottocode", "ISO 639-3" joined by a Y-shaped connector to a
single dot, captioned in 8pt gray: "one language, three identifiers".
Below it, a small note box with two short lines of 8pt gray text.

The spine's bottom exits with one arrow into a gray database glyph rendered as three
thin stacked ellipses (a minimal cylinder, outline only, no fill), labeled
"9 tables · 157,736 rows" in monospace.

From the database, one arrow right to three small file nodes stacked vertically,
each outline-only with a folded corner, labeled
"languages.json 0.9 MB", "digital_presence.json 2.2 MB", "feature_matrix.json 4.9 MB".

From the file nodes, three thin arrows into a final moss-green outlined rectangle
labeled "one JSON contract → Pinia store", with a monospace sublabel "no view code changes".

Place one small inset thumbnail (a 1px-framed screenshot of a dense data matrix,
mostly empty cells, sparsely populated) at the far right bottom, about 15% of canvas
width, connected by a single thin label line reading "15.0% fill".

Text is English, minimal. Numbers in monospace. Only desaturated brick red, slate blue,
moss green and warm gray — no rainbow, no saturated hues.
Style constraints: flat vector, 1px hairline strokes, no gradients, no drop shadows,
no 3D, no bevels, no emoji, no clip-art, no decorative frames, left-aligned labels,
publication figure quality, 300 dpi.
```

---

## 3. 负向提示词（所有图都加上）

```
rainbow palette, neon colors, saturated cyan, magenta, purple, gradient fills,
glassmorphism, glossy 3D icons, isometric buildings, drop shadows, glows,
stock-photo people, emoji, clip-art, cartoon mascots, rounded blob shapes,
decorative borders, paper texture, watermark, skewed perspective, cluttered layout,
centered paragraphs of text, tiny unreadable text
```

---

## 4. 实操建议（很重要，能省掉大量返工）

**① 生图模型不擅长文字，尤其是中文。**
实测顺序：`英文标签 + 后期在 PPT/Word 里叠中文` > `英文标签直接用` > `中文标签`。
若一定要中文，优先用 **代码绘图**（下面 ②），而不是图像模型。

**② 这两张图其实更适合用代码画，而不是生图。**
它们都是**结构图**，节点数固定、连线确定。用生图会出现"文字错、节点数不对、连线接错"，
而且改一次要重生一次。可靠的替代方案：

| 方案 | 优点 | 适合 |
|---|---|---|
| **Graphviz / Mermaid** | 布局自动、文字绝对正确 | 流程图 |
| **draw.io → SVG** | 手控位置、可导出矢量 | 架构图 |
| **Matplotlib + 指定色板** | 与论文其余图风格统一 | 两图都可以 |

如果你愿意，我可以**直接用代码生成这两张图**（SVG/PNG，按上面的配色和结构，
文字直接是中文），这样既不用生图、也不会出现错字，还能和论文里其余 12 张图风格一致。
