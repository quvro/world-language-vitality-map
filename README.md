# 世界语言赛博活力图谱

数据可视化与人机交互课程项目。

把四个独立数据源对齐成一张可分析的宽表，回答一个具体问题：
**什么样的语言，正在数字化的浪潮里被抛下？**

- 设计文档：[docs/plans/2026-10-07-language-vitality-design.md](docs/plans/2026-10-07-language-vitality-design.md)
- 数据校验报告：[data/processed/validation.md](data/processed/validation.md)

---

## ⚠️ 先说清楚：「活力」在这项目里指什么

**这是全项目最容易被追问、也最需要自己先说清楚的一点。**

标题里的限定词是「**赛博**」活力 —— 它说的是**一门语言在数字空间里的活跃程度**，
而不是「还有多少人在说这门语言」。界面上的简称一度丢掉了这个限定词，造成歧义，现已改正。

项目里所有叫"活力"的指标，原始量只有一个：**该语言的维基百科版本的月浏览量**
（Wikimedia Pageviews REST API，`all-access/user/monthly`）。它其实是三个不同的量：

| 界面位置 | 实际算的是什么 |
|---|---|
| 地图点的大小 | 当月浏览量的两种尺度（相对自身十年峰值 / 当月跨语言排名分位） |
| 地图点的颜色、活力变化图 | 十年变化率 `(末3月月均 − 首3月月均) / 首3月月均` |
| 时间轴折线 | 筛选范围内浏览量的逐月合计 |

**它测的是「数字关注度」，不是语言学意义上的「语言活力」。** 后者有成熟定义
（UNESCO 的 9 项指标：代际传承、使用者绝对人数、使用场合、政策、社区态度……），
核心是代际传承与实际使用。两者的差距是有方向的：

- **门槛偏差**：维基百科是"读"的，要求有文字传统 + 网络接入人口，
  所以系统性低估无文字传统的语言
- **人口偏差**：`浏览量 ≈ 使用者数 × 识字率 × 上网率 × 用维基的习惯`，
  四项相乘会**放大**差距 —— 实测末月最高（English 72.3 亿）与最低（Pipil 1,211）
  差 **597 万倍**，但语言活力的差距绝没有这么大
- **反向可能**：使用者很多但都去读英文维基的语言，会被显示成"不活跃"
- **覆盖极窄**：2,662 门语言里只有 **263 门**算得出增长率（9.9%），
  而且系统性地是那些本就被记录得最全、上网人口最多的语言

### 所以我们补了第二个维度

只测数字关注度是不够的。项目接入了 **UNESCO 濒危等级**
（Wikidata `P1999`，`pipeline/05_fetch_endangerment.py`），
于是两个独立的维度可以对照：

> **一门语言在语言学上还活着，但在数字空间里已经死了吗？反过来呢？**

实测两者高度一致，而且陡峭：

| UNESCO 等级 | 语言数 | 有维基百科版本 |
|---|---|---|
| 1 safe（安全） | 82 | **75.6%** |
| 2 vulnerable（脆弱） | 314 | 12.4% |
| 3 definitely endangered（明确濒危） | 268 | 9.3% |
| 4 severely endangered（严重濒危） | 203 | 4.4% |
| 5 critically endangered（极度濒危） | 198 | **2.0%** |
| 6 extinct（已灭绝） | 51 | **0.0%** |

**严格单调。已灭绝的 51 种语言，一个有维基百科版本的都没有。**

> **口径警示（必须一起讲）**：UNESCO 名录**只收濒危语言** ——
> 全名录 2,593 条里只有 82 条是 safe。所以「未被名录收录」**不等于**「安全」，
> 不能反推。本项目 2,662 门语言里有 1,546 门未匹配，其中 1,418 门没有维基版本；
> 它们只是"不在名录里"，不代表它们状况良好。
>
> 另外，「强度」维度（有维基版本者的阅读量中位数）样本很小 ——
> 严重濒危档只有 9 门、极度濒危档只有 3 门，**不足以支撑结论**，
> 界面上已如实标注，仅供参照。

---

## 当前数据规模（已构建）

| 数据集 | 规模 |
|---|---|
| `dim_language` | 3,573 条原始记录，其中 **2,662 条是真语言**（另 911 条是 WALS 的语系/语族/语支层级占位行，导出前端时已剔除） |
| `fact_language_feature` | **76,475 条**（2,660 语言 × 192 特征） |
| `feature_vector`（宽表） | 2,660 × 192，填充率 15.0%（含缺失掩码） |
| `fact_language_timeseries` | **55,427 条**（244 个语言 × 127 个月 × 浏览量/编辑量） |
| 维基语言版本 | 364 个，其中 **247 个可关联到 WALS** |
| **合计** | **约 13.2 万条结构化记录** |

特征覆盖率（决定条件对比交互能用哪些特征）：
每特征覆盖语言数**中位数 257**，**88 个特征覆盖 ≥ 300 种语言**，
覆盖最好的是语序类特征（"Order of Object and Verb" 覆盖 1,495 种语言）。

### 一个已经看得到的结论

用「首 3 月均值 vs 末 3 月均值」算 10 年变化（已剔除基线不可靠的统计伪影）：

| 方向 | 语言 |
|---|---|
| **下滑** | 西班牙语(加那利) −48.6%、葡萄牙语 −44.6%、他加禄语 −52.1%、藏语(书面) −48.9% |
| **增长** | 达格班语 +4210%、拉定语 +4050%、汤加语 +3053%、巴厘语 +2151%、豪萨语 +1486% |

欧洲老牌语言在退、非洲与亚洲语言在进——这就是 pre 时可以讲的核心发现。

---

## 目录结构

```
keshihua/
├── pipeline/              数据管道（Python，仅用标准库 + pandas）
│   ├── common.py          公共模块：路径、HTTP、GitHub blob、WDQS、月份归一
│   ├── 01_fetch_sources.py    WALS 六表 + Wikidata ISO 映射
│   ├── 02_fetch_wikimedia.py  维基百科逐语言版本时间序列（可续抓）
│   └── 03_build_dataset.py    构建 SQLite + 前端 JSON + 校验报告
├── data/
│   ├── raw/               原始数据（只增不改）
│   │   ├── wals/          WALS CLDF 六表
│   │   ├── wikimedia/     pageviews / edits / join
│   │   └── xref/          ISO 639-1 ↔ 639-3 映射
│   └── processed/         SQLite + 前端用 JSON + 校验报告
├── docs/plans/            设计文档
├── _tools/                选型阶段的探测脚本（保留备查）
└── _refs_out/             探测输出
```

---

## 运行数据管道

需要 Python 3.11+ 与 pandas。本仓库使用的解释器：

```
C:\Users\sunyn\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe
```

```powershell
$py = 'C:\Users\sunyn\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'

& $py pipeline\01_fetch_sources.py      # WALS 六表 + ISO 映射（约 1 分钟）
& $py pipeline\02_fetch_wikimedia.py    # 时间序列（约 10~20 分钟，可中断续抓）
& $py pipeline\03_build_dataset.py      # 构建 SQLite 与前端 JSON（约 30 秒）
& $py pipeline\04_fetch_zh_labels.py    # 中文标签（3 次 WDQS 查询，约 4 分钟）
& $py pipeline\check_dataset.py         # 完整性自检
```

常用参数：

| 参数 | 作用 |
|---|---|
| `--force` | 忽略已有文件，重新抓取 |
| `--only-joined` | 只抓能关联到 WALS 的 247 个语言版本（02） |
| `--limit=N` | 只抓前 N 个（调试用，02） |

四个脚本都是**幂等**的：重复运行会跳过已完成的文件 / 已抓取的语言。
`04` 会把中文标签同时写到 `data/raw/xref/`（缓存）与 `data/processed/`（前端读取）。

---

## 运行前端

```powershell
$node = 'C:\Users\sunyn\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
$pnpm = 'C:\Users\sunyn\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\pnpm\bin\pnpm.mjs'

cd web
& $node $pnpm install          # 首次
& $node 'node_modules\vite\bin\vite.js' --host 127.0.0.1 --port 5173
```

打开 **http://127.0.0.1:5173/**

> ⚠️ **本机必须放宽权限才能起开发服务器。** Vite 依赖 esbuild，而 esbuild 需要
> 启动子进程并通过管道通信；沙箱会拒绝该子进程（`spawn EPERM`）。
> 这不是代码问题，换一台没有沙箱的机器直接 `pnpm dev` 即可。

### 前端结构

```
web/
├── index.html / vite.config.ts / tsconfig.json
├── public/vendor/        原样提供、不参与打包的静态资源
│   ├── echarts.min.js
│   └── world.js          ECharts 世界地图注册脚本（传统 script，非 ESM）
├── src/
│   ├── theme/            tokens.css（唯一真源）+ echarts-theme.js（从 token 读色）
│   ├── stores/dataset.ts Pinia：全局筛选 / 时间位置 / 选中状态
│   ├── components/       WorldMap · GrowthChart · FeatureCoverage
│   │                     FilterPanel · LanguageCard · VitalityTimeline
│   ├── App.vue           导航布局与状态分发
│   └── types.ts
└── preview/              零构建的静态预览页（数据管道的独立验证，可保留）
```

设计要点：

- **地图没有「有时间 / 没时间」的模式划分。** 活力层永远在线、大小永远由时间轴驱动，
  所以拖时间轴**一定**有可见反馈。早期版本用「语区分布 / 数字活力」两个模式互斥切换
  整套数据集，导致在分布模式下拖时间轴毫无反应、切到活力模式地图又会空掉一大半 ——
  这是设计缺陷而非 bug，已通过去掉模式划分解决。着色依据（按语区 / 按趋势）是另一个
  正交开关。
- **点的大小用 series 级 `symbolSize` 回调**（当月浏览量放在 `value[2]`），
  而不是逐项 `symbolSize` 属性 —— 回调每次渲染都重新求值，更新更可靠也更容易补间。
- **所有视图只读 Pinia store、彼此不直接调用** —— 这是"任一处选中、全局同步"的前提，
  也让新增一个视图不需要改动别的模块（对应设计文档 §10 的注册表约定）。
- **store 同时维护 `selected` 与 `comparisonSet`** —— 为"多语言并排对比"扩展留口。
- **时间轴与 mini 折线是手写的**，不用组件库 —— 签名交互要看起来原创。
- **颜色一律从 `tokens.css` 读**，图表不写死 hex，换肤只改一处。

### 全是可在本机跑的验证脚本

本机没有无头浏览器，但这些都能在 Node 里跑（ECharts 5.6 支持无 DOM 的 SSR 渲染）：

```powershell
$node = 'C:\Users\sunyn\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe'
& $node web\preview\verify-timeline-render.mjs   # 时间轴是否改变地图渲染（7/7 输出不同）
& $node web\preview\verify-size-scale.mjs        # 点大小尺度：相邻月份变化是否够大
& $node web\preview\verify-compare-signal.mjs    # 条件对比是否有信号
& $node web\preview\verify-zh-names.mjs          # 中文名覆盖率
& $node web\preview\verify-data.mjs              # 前端数据处理的假设是否成立
```

诊断脚本（排查用）：`diagnose-months.mjs`（时间轴月份是否完整）、
`diagnose-scale.mjs`（尺寸尺度对比）、`repro-merge-bug.mjs`（ECharts merge 更新是否生效）。

### 三个签名交互

| 交互 | 做什么 | 可验证性 |
|---|---|---|
| **时间轴回放** | 拖动 2015-07 → 2026-01，地图上点的大小随之变化 | `verify-timeline-render.mjs`（SSR 渲染比对） |
| **条件对比** | 选一个语法特征，按取值分组，比较各组的**数字在场率**与十年趋势 | `verify-compare-signal.mjs`（确认有信号） |
| **自然语言查询** | 一句话 → 结构化筛选条件 → 全部视图联动 → 基于真实数据生成解释 | `verify-nl-local.mjs`（12 个问法端到端） |

**条件对比默认展示哪个特征，是自动算出来的**，不是拍脑袋定的。
实测发现语序这类"常识型"特征其实差异极小（SVO 15% vs SOV 10%，仅 4 个百分点），
默认展示它会让整个界面显得没信息。所以启动时会遍历 192 个特征、
挑**分组差异最大**的那个作为默认（当前是 `122A` Relativization on Subjects，极差 83 个百分点）：

```
关系代词   12 门   数字在场率 92%
Gap       125 门   数字在场率 30%
非缩减     24 门   数字在场率  8%
```

左侧列表同时给出**覆盖率**（数据够不够对比）与**分组差异**（值不值得对比），并按后者排序。
点一个分组会联动过滤全站视图（地图、增长图同步收窄）。

> 设计上有一处必须注意：分组统计走的是 `store.filteredBase`（**不含**特征筛选），
> 否则点选一个分组后其它分组会消失、对比图自己塌掉。

---

## 导航：五个视图

| 选项卡 | 视图 | 回答什么问题 |
|---|---|---|
| **地图** | `WorldMap` | 这些语言在哪里？谁在数字空间活着？（点大小随时间轴变化） |
| **活力变化** | `GrowthChart` | 十年里谁在退、谁在进？ |
| **条件对比** | `FeatureCompare` | 语法结构不同的语言，数字处境有差异吗？ |
| **记录缺口** | `FeatureMatrix` | **数据集本身**有多不完整？记录偏差长什么样？ |
| **活力之辨** | `EndangermentView` | 语言学上的濒危程度，和数字空间的存在性对得上吗？ |

所有视图**只读同一个 Pinia store、互不直接调用** ——
任一处选中或筛选，全局同步；新增视图不需要改其他模块。

---

## 自然语言查询（P5）

**闭环**：`自然语言 → 结构化意图 → 写入 store → 地图/图表/时间轴联动 → 基于真实筛选结果生成一句话解释`。

底部常驻输入条，解析结果会以「条件标签」的形式显示出来 ——
**让用户看得见它理解成了什么**，而不是一个黑盒聊天框。

**两条解析通路，互为兜底：**

| 通路 | 触发条件 | 说明 |
|---|---|---|
| **大模型** | 配置了密钥 | 走 `POST /api/nl`，由 Vite 中间件转发 |
| **本地规则** | 没密钥 / 调用失败 | `web/shared/intent.js` 的 `parseLocal()`，功能不中断 |

**密钥永远不进浏览器**：前端只请求同域的 `/api/nl`，由 Vite 中间件拿服务端密钥去调大模型。
这样既避免密钥被抓包，也绕开了大模型接口不开放浏览器 CORS 的问题。

配置方式（环境变量，均可选，设好后重启 vite）：

```powershell
$env:DEEPSEEK_API_KEY = 'sk-...'                  # 或 $env:LLM_API_KEY
$env:LLM_BASE_URL = 'https://api.deepseek.com'    # 默认值
$env:LLM_MODEL = 'deepseek-chat'                  # 默认值
```

任何 OpenAI 兼容接口都可用（SiliconFlow、Moonshot、智谱等只需改 `LLM_BASE_URL` 与 `LLM_MODEL`）。

**一个刻意的职责划分**：模型**只负责把话翻译成筛选条件，不负责算数**。
解释里的统计数字一律在前端按实际筛选结果算出，所以与视图里的数字必然一致 ——
避免大模型应用里很常见的「模型编了个数」。

### 本地解析器踩过的两个坑

1. **标签 ≠ 数值编码。** 矩阵里存的是 WALS 的数值编码（`values.csv` 的 `Value` 列，如 `"2"`），
   而人和大模型说的是标签（`"SOV"`）。必须先经 `codes.csv` 把标签转成 `Number`，
   否则「语序是 SOV 的语言」永远筛出 0 条。**这个坑对大模型通路同样成立。**
2. **ASCII 关键词必须按词边界匹配。** 用 `includes` 时 `"Indo-European"` 会被 `europe` 命中、
   `"Austro-Asiatic"` 会被 `asia` 命中，于是「印欧语系中有声调的语言」被误加上「语区=欧亚」。
   中文没有词边界概念，仍旧用 `includes`。

---

## 记录缺口图（M4）

这是设计文档 P3 里规划的「三个核心视图」之一（地图 + 时间轴 + **特征矩阵**），
补上后导航变成四个选项卡。

**它讲的是数据集自身的结构，不是语言本身。** WALS 的 2,660 × 192 矩阵
**只有 15.0% 有值**，特征覆盖率中位数仅 **9.7%**（2,660 门语言里只有 257 门
被记录了这一条特征）；192 个特征里只有 4 个覆盖率超过 50%。

视图分两块：

- **记录密度矩阵**：x = 192 个特征（按覆盖率降序），y = 语言（按记录完整度降序）。
  每格颜色 = 该行语言组中"有这条特征记录"的比例。左上密、右下空 ——
  这个阶梯形状就是"记录集中在少数语言与少数特征上"的视觉形态
  （左上角 85.0% vs 右下角 1.1%，差 74 倍）。
- **双重缺席**：按记录完整度分桶，看拥有维基百科版本的比例。

| WALS 收录特征数 | 语言数 | 有维基版本 |
|---|---|---|
| < 30 | 1,664 | **5.6%** |
| 30–79 | 784 | 13.5% |
| 80–149 | 200 | 27.0% |
| ≥ 150 | 14 | **92.9%** |

**结论：语言学界记录得越少的语言，在数字世界里往往也越不可见。**
这两件事本来分属语言学的记录偏差与互联网的使用偏差，
放在同一张图里才看得出它们是叠加的 —— 这正是这个项目的主题。

> 用 canvas 手绘而非 ECharts：51 万格 heatmap 系列扛不住。
> 先画进一张 `cols×rows` 的离屏画布再缩放贴上来，顺带得到密度图该有的平滑感。
> 验证见 `verify-feature-matrix.mjs`（含阶梯形状与分桶比例的双重校验）。

### 做这个视图时挖出的数据问题

WALS 的 `languages.csv` 共 3,573 行，但其中 **911 行根本不是语言**，
而是**语系 / 语族 / 语支的层级占位行**（ID 形如 `family-abun`、`genus-berber`、
`subfamily-chadic`）。真正的语言只有 **2,662 行**。

不区分它们的后果很实际：顶栏「语言数」虚高约 900；这些行的 `Family` 为空，
于是语系筛选里多出一个巨大的「未分类」桶；搜 `Chadic` 会搜出语系占位行。

修法：`dim_language` **保留全部 3,573 行原始记录**并新增 `kind` 列标注类型，
但导出给前端的 `languages.json` 只含 2,662 门真语言。
（这个数字差异也解释了为什么"双重缺席"首档会从 2,575 门降到 1,664 门。）

### 前端踩过的坑

1. **命令式渲染的组件，别逐字段枚举 watcher。**
   ECharts 不是响应式的：状态变了必须有人显式调 `render()`。
   地图组件原本写成 `watch(() => store.colorBy, …)` 这样一个个字段列出来 ——
   后来给「只看选中」加了 `store.hideUnselected`、也写进了 computed 的过滤逻辑，
   **却忘了加对应的 watcher**，于是那个开关点了完全没反应，
   而且因为 computed 确实重算了，从代码上看不出任何异常。
   改成**直接盯住要画的数据本身**（`watch([contextData, vitalityData, haloData], …)`）：
   数据变了就一定重画，不可能再漏。
   只为「渲染时读取、不进数据」的选项（`sizeMode` 在 symbolSize 回调里读、
   `showVitality` 决定 series.data 是否为空）和会改变 `geo.nameMap` 的 `lang` 保留显式 watcher。
   回归防线见 `web/preview/verify-map-repaint.mjs` ——
   它逐字段检查 WorldMap 里读到的每个 store 字段是否都能触发重绘，
   并强制「有理由的例外」写清理由。
   顺带说明：选中变化要用**合并**渲染（`setOption({series})`）而不是
   `setOption(opt, true)`，后者会重建 geo 组件、把用户拖好的缩放和平移一起重置。

2. **密集点图里，「加粗描边 + 放大几像素」不足以标出选中项。**
   描边色和点本身的填充色同属一个色系，视觉上会糊在一起。
   最终做成**靶心**：选中点填满不透明 + 白色内圈，外面再罩一个强调色的**空心大圈**
   （单独一个 `silent: true` 的 scatter 系列，否则环会吃掉鼠标事件、
   挡住底下点的 tooltip）。环的半径随该点当前大小变化，才不会忽大忽小；
   并且在活力层里找不到该点时要退回底图 —— 否则选到一门**没有维基版本**的语言
   （活力层里根本没有它）时，环就不会出现。

3. **`public/` 之外的传统 script 会被 Vite 转成 ES module。**
   `world.js`（147 KB）被转换后变成 825 KB 且含 `export`，用 `<script>` 标签加载会直接
   语法报错。放进 `public/vendor/` 后 Vite 原样提供，问题消失。
4. **编辑器原子写产生的 `.*.tmpdir` 会让 Vite 监听器 EBUSY 崩溃。**
   已在 `vite.config.ts` 的 `server.watch.ignored` 中排除。
5. **pnpm 11 的构建白名单键是 `allowBuilds`（在 `pnpm-workspace.yaml`），**
   不是 package.json 里的 `pnpm.onlyBuiltDependencies`（那个已失效）。
   不放开 `esbuild` 就不会落地平台二进制，Vite 起不来。
6. **点的大小用「当月浏览量 / 当月全局最大」是错的 —— 会看起来像"点了没反应"。**
   德语维基月浏览约 7 亿，多数语言只有几千。开方压缩后几乎所有点都被挤在最小尺寸附近：
   实测拖时间轴时尺寸**中位变化仅 0.05 px**，只有 **0.3%** 的变化肉眼可辨。
   地图其实一直在更新，但变化量是人眼分辨率的二十分之一。
   改成**相对该语言自身十年峰值**后中位变化 1.96 px、**59.7%** 可辨。
   教训：**尺度选错会让正确的交互看起来完全失效**，而且这种问题"代码能编译、SSR 也能渲染出不同结果"，
   只有量化「相邻状态之间的差异是否达到感知阈值」才能发现。
5. **两个并发注意点**：`symbolSize` 回调不要把关键数据放在 `params` 参数里
   （不确定 ECharts 是否传），应当编进 `value` 数组；`symbolSize` 用 series 级回调、
   更新用 merge 而非 `notMerge`，否则补间动画会丢。
6. **TS 对象里含连字符的键必须加引号**：`Chukotko-Kamchatkan: ...` 会让 esbuild 在
   `-` 处报 `Expected "}" but found "-"`。这类语系名有一堆，留意。

---

## ⚠️ 本机网络限制（实测，非推测）

这台机器上有几个域名不可达，管道已针对性绕过：

| 域名 | 状态（直连） | 状态（开代理后） | 绕法 |
|---|---|---|---|
| `api.github.com` | ✅ 可达 | ✅ | 主用。git blob 接口取文件（base64） |
| `github.com` | ❌ 不可达 | ✅ 可达 | 直连时改用 blob 接口 |
| `raw.githubusercontent.com` | ❌ 不可达 | ❌ 仍不可达 | **始终走 blob 接口** |
| `registry.npmjs.org` | ❌ 不可达 | ✅ 可达 | 开代理后才能 `pnpm install` |
| `cdn.jsdelivr.net` | ✅ 可达 | ✅ | 主用，下载 ECharts 等前端资源 |
| `unpkg.com` | ❌ 不可达 | ❌ 仍不可达 | 改用 jsDelivr |
| `*.wikipedia.org` | ❌ 不可达 | ✅ 可达 | 时间序列本来就不依赖它 |
| `wikimedia.org/api/rest_v1` | ✅ 可达 | ✅ | 浏览量 / 编辑量时间序列 |
| `meta.wikimedia.org` | ✅ 可达 | ✅ | 语言版本清单（sitematrix） |
| `query.wikidata.org` | ⚠️ 可达但限流 | ⚠️ 同样限流 | **约 1 次/分钟**，结果必须缓存 |

**规律**：`api.github.com`、`cdn.jsdelivr.net`、`wikimedia.org` 一直可用；
`raw.githubusercontent.com` 和 `unpkg.com` 即使开代理也不通；
npm registry 和 `*.wikipedia.org` 需要代理。管道已按此选择绕法，换网络环境也不用改代码。

---

## 数据字典

### SQLite：`data/processed/language_vitality.db`

| 表 | 内容 | 关键字段 |
|---|---|---|
| `dim_language` | 语言/变体主表 | **`wals_id`（主键，唯一）**, `glottocode`（**非唯一**，语言级分组键）, `name`, `latitude`, `longitude`, `family`, `subfamily`, `genus`, `iso639p3`, `macroarea` |
| `dim_feature` | 192 个语法特征定义 | `feature_id`, `name`, `description` |
| `dim_code` | 1,143 个特征取值定义 | `code_id`, `feature_id`, `name`, `number` |
| `fact_language_feature` | 语言 × 特征 × 取值（长表） | `wals_id`, `feature_id`, `value_raw`, `code_id` |
| `feature_vector` | **物化的宽表** | `wals_id` + 192 个特征列 |
| `fact_language_timeseries` | 逐月浏览量 / 编辑量 | `wals_id`, `wiki_code`, `month`(YYYYMM), `metric`, `value` |
| `dim_wiki_edition` | 维基语言版本与关联情况 | `wiki_code`, `joined`, `hop`, `wals_id`, `join_ambiguous`, `iso_candidates` |
| `dim_genealogy` | 254 个语系谱系树 | — |
| `xref_iso` | ISO 639-1 ↔ 639-3 | `iso1`, `iso3` |

### 前端 JSON：`data/processed/`

| 文件 | 用途 |
|---|---|
| `languages.json` | 地图点位与语言元数据（含 `wiki_code` 与活力摘要 `growth`）|
| `timeseries.json` | 按语言组织的月度序列（`views` / `edits`），时间轴回放用 |
| `features.json` | 特征与取值定义，供筛选器与图例使用 |
| `feature_matrix.json` | 列式存储的 192 维特征矩阵，供条件对比与相似度检索 |

---

## 设计上的关键约定（见设计文档 §10）

这三条是**现在就必须做对**的决定，否则加扩展功能时要重做数据层：

1. **主键用 `wals_id`（唯一），`glottocode` 是非唯一的分组键** ——
   这是**实测后更正过**的决定。原设计想用 Glottocode 作主键以便日后接方言，
   但实测发现 WALS 里 Glottocode 不唯一：2,662 条真语言记录只有 2,502 个 Glottocode，
   93 个 Glottocode 覆盖 2~6 个**取值互相冲突**的变体（`basq1248` 有 11 个）。
   用它作主键会静默合并数据。改成 `wals_id` 作主键后反而得到了**变体级 + 语言级
   两个粒度**，接方言时新增行给各自 ID 与 Glottocode 即可。
2. **物化 `feature_vector` 宽表** —— 让"按特征找语言"与条件对比交互无需运行时透视。
   同时保留**缺失掩码**语义：空值表示"WALS 未收录"，而不是"该语言没有这个特征"。
3. **月份统一归一为 `YYYYMM`** —— 两个维基端点的时间戳格式不一致
   （pageviews 是 `2015070100`，edits 是 ISO `2015-07-01T00:00:00.000Z`），
   不归一会静默产生 `2015-0` 这种错误键，且**原始月份信息不可恢复**
   （必须重抓；管道现在会主动检测并只重抓受影响的序列）。
4. **跨源关联的不确定性显式落库** —— `dim_wiki_edition.join_ambiguous` /
   `iso_candidates`。实测 247 个关联**全部**是多对一：因为 ISO 639-3 标识「语言」
   而 WALS 收录「变体」。这不是错误，但要记录我们的择优规则（取特征数据最丰富者，
   并列时按 `wals_id` 保证确定性），以便复核。

---

## 踩过的坑（记录在此，避免重复踩）

1. **维基 REST API 限流很凶**：0.2 秒间隔会导致大部分请求返回 429。
   现在用 1.5 秒间隔 + 尊重 `Retry-After` 的退避。
2. **`http_get` 不能把所有异常都包成 `RuntimeError`**：否则调用方拿不到
   HTTP 状态码，404（该维基无此数据）和 429（限流）就无法区分，会白白重试。
3. **部分小语种维基没有编辑量数据**，`/edits/` 直接返回 404 —— 这是正常的，已优雅降级。
4. **Met 博物馆 API 的搜索端点已下线**（410）——本项目不用，但记录备查。

---

## 数据来源

| 来源 | 许可 / 说明 |
|---|---|
| [WALS Online](https://wals.info/) (CLDF) | 学术开放数据，引用须注明 Dryer & Haspelmath (eds.) |
| [Wikimedia REST API](https://wikimedia.org/api/rest_v1/) | CC BY-SA |
| [Wikidata](https://query.wikidata.org/) | CC0 |
| [D-PLACE](https://d-place.org/) | 第三阶段接入 |

> 答辩要点：**我们没有现成的宽表**——三个数据源的语言标识体系各不相同
> （WALS 用自增 ID 与 ISO 639-3，维基用语言子域码混用 ISO 639-1/639-3），
> 是我们自己构建了 185 组 ISO 映射把 247 个语言对齐起来的。
