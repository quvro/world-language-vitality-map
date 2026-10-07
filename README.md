# 「正在消失的声音」——数字时代的语言生存图谱

数据可视化与人机交互课程项目。

把三个独立数据源对齐成一张可分析的宽表，回答一个具体问题：
**什么样的语言，正在数字化的浪潮里被抛下？**

- 设计文档：[docs/plans/2026-10-07-language-vitality-design.md](docs/plans/2026-10-07-language-vitality-design.md)
- 数据校验报告：[data/processed/validation.md](data/processed/validation.md)

---

## 当前数据规模（已构建）

| 数据集 | 规模 |
|---|---|
| `dim_language` | 3,573 条语言记录，其中 **2,662 条有经纬度** |
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
```

常用参数：

| 参数 | 作用 |
|---|---|
| `--force` | 忽略已有文件，重新抓取 |
| `--only-joined` | 只抓能关联到 WALS 的 247 个语言版本 |
| `--limit=N` | 只抓前 N 个（调试用） |

三个脚本都是**幂等**的：重复运行会跳过已完成的文件 / 已抓取的语言。

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

### 怎么验证「拖时间轴地图真的有反应」

本机没有无头浏览器，但 ECharts 5.6 支持无 DOM 的 SSR 渲染，所以这件事是可测的：

```powershell
& $node web\preview\verify-timeline-render.mjs
```

它会在 Node 里对 7 个时间点各渲染一次 SVG 并比对 hash。当前结果：**7/7 输出互不相同**，
SVG 体积随月份单调增长，绘制符号数 2,845 → 2,890（差值 45 = 当月有数据的语言 195 → 240）。

### 前端踩过的坑

1. **`public/` 之外的传统 script 会被 Vite 转成 ES module。**
   `world.js`（147 KB）被转换后变成 825 KB 且含 `export`，用 `<script>` 标签加载会直接
   语法报错。放进 `public/vendor/` 后 Vite 原样提供，问题消失。
2. **编辑器原子写产生的 `.*.tmpdir` 会让 Vite 监听器 EBUSY 崩溃。**
   已在 `vite.config.ts` 的 `server.watch.ignored` 中排除。
3. **pnpm 11 的构建白名单键是 `allowBuilds`（在 `pnpm-workspace.yaml`），**
   不是 package.json 里的 `pnpm.onlyBuiltDependencies`（那个已失效）。
   不放开 `esbuild` 就不会落地平台二进制，Vite 起不来。

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
   但实测发现 WALS 里 Glottocode 不唯一：3,573 条记录只有 2,502 个 Glottocode，
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
