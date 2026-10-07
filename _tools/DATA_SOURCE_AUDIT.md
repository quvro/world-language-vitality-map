# 数据源可行性审计报告 — 民俗 / 神话 / 神秘学 (Data Source Feasibility Audit)

**审计人**: 子代理 (delegated auditor) · **方法**: 原创脚本 + 实际 HTTP 抓取（非搜索摘要）
**Python**: `C:\Users\sunyn\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
**证据/脚本目录**: `E:\develop\myprogram\keshihua\_tools\`
**抓取时间**: 2026-10-06/07 (依据 WDQS 响应头 `Date` 与站点页脚日期)
**关键产物**: `project_full.json` (3610 行)、`representative_full.json` (3995 行)、`project_4234.json` (4234 行)

> 标注约定：**[VERIFIED]** = 我实际发出了请求并看到了数据；**[UNVERIFIED]** = 仅来自搜索片段或我无法读取的页面。

---

## A. 中国非物质文化遗产（官方结构化数据）

### A.1 站点拓扑与别名关系

| URL | 结果 | 说明 |
|---|---|---|
| [https://www.ihchina.cn/](https://www.ihchina.cn/) | **[VERIFIED]** HTTP 200 | 主页，页脚注明数据统计截至 2025-03-13，首页自报 **3610 项 / 3998 人** |
| `http://www.ihchina.cn/project` | **[VERIFIED]** HTTP 200, 43255 B | 与 `/project.html` 返回**完全同字节**的 HTML（同一页面） |
| `http://www.ihchina.cn/project.html` | **[VERIFIED]** HTTP 200, 43255 B | 项目名录页 |
| `http://www.ihchina.cn/representative.html` | **[VERIFIED]** HTTP 200, 40356 B | 传承人页（正文自报 **3994 人**，截至 2025-12） |
| [http://test.nrcca.org.cn/representative.html](http://test.nrcca.org.cn/representative.html) | **[VERIFIED]** HTTP 200, 40331 B | 与 ihchina 同源同构 |
| `https://www.nrcca.org.cn/` | **[VERIFIED] 失败** | `SSLCertVerificationError: Hostname mismatch, certificate is not valid for 'www.nrcca.org.cn'` |
| `http://www.nrcca.org.cn/` | **[VERIFIED]** HTTP 200, 95873 B | 仅 HTTP 可用 |
| `https://nrcca.org.cn/` (无 www) | **[VERIFIED] DNS 解析失败** | `gaierror 11001` |
| `http(s)://.../robots.txt` | **[VERIFIED] HTTP 404**（两个域名均是） | **无 robots.txt，无 CAPTCHA，无登录，未观察到限速** |

**重要结论 [VERIFIED]**：`nrcca.org.cn` **不是独立数据源，而是 `ihchina.cn` 的完整镜像/别名**。同一接口在 `test.nrcca.org.cn`、`www.nrcca.org.cn`、`www.ihchina.cn` 上返回**逐字节完全相同**的响应（传承人 7,169,900 B；项目 18,012,594 B）。所以 A 部分只需审计一个后端。另外 `https://www.nrcca.org.cn` 的 TLS 证书主机名不匹配，脚本里用 HTTPS 会直接抛异常 —— 这是学生最容易踩的坑之一。

### A.2 (1) 国家级非遗代表性项目名录 —— 可用接口

列表页 `project.html` 的表头字段（HTML 静态渲染，但**默认无数据**，`搜索结果：共 0 条 / 暂无数据`）：

> 序号 | 项目序号 | 编号 | 名称 | 类别 | 公布时间 | 类型 | 申报地区或单位 | 保护单位

数据由 JS 通过 `$.get("/getProject.html", params)` 填充。**实际的 JSON 端点 [VERIFIED]**：

```
https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1
```

→ HTTP 200，**`application/json`**，**18,012,594 B**，`total=3610`，**`list` 长度 = 3610**，耗时 **10.6 s**，一次请求拿全。已存 `_tools/project_full.json`。

**逐字段实测覆盖率（3610 行）**：

| JSON 字段 | 中文含义 | 非空数 |
|---|---|---|
| `num` | **编号**（如 `Ⅰ-1`） | 3610/3610 |
| `auto_id` | **项目序号**（如 `1`） | 3610/3610 |
| `title` | **名称**（如 `苗族古歌`） | 3610/3610 |
| `type` | **类别**（如 `民间文学`） | 3610/3610 |
| `rx_time` | **公布时间/批次**（如 `2006</br>(第一批)`） | 3610/3610 |
| `cate` | **类型**（`新增项目`/`扩展项目`） | 3610/3610 |
| `province` | **申报地区或单位** | 3610/3610 |
| `protect_unit` | **保护单位**（如 `台江县非物质文化遗产保护中心`） | 3608/3610 |
| `project_num` | 内部子项号（`Ⅰ-001_01_522630`） | 3610/3610 |
| `content` | 项目简介全文 | 3610/3610 |
| `id` | 详情页 ID → `/project_details/{id}.html` | 3610/3610 |
| `address`/`city`/`area` | 行政区划代码 | 3541 / 3340 / 2348 |

数据自洽性校验 **[VERIFIED]**：3610 行 ID 全部唯一；类别分布与首页数字**逐一吻合**（传统技艺 629、民俗 492、传统戏剧 473、传统音乐 431、传统美术 417、传统舞蹈 356、民间文学 251、曲艺 213、传统医药 182、传统体育游艺与杂技 166，合计 3610）；批次分布 2006:763 / 2008:1352 / 2011:567 / 2014:463 / 2021:465，合计 3610；类型分布 新增 2278 + 扩展 1332 = 3610。**即抓取是完整且无重复的。**
另有独立 `num`（国家级项目编号）**1574 个**、独立 `title` 3062 个、独立 `province` 1916 个 —— 对应官方说法"共 1557 个项目、按申报地区逐一统计共 3610 个子项"。

### A.3 (2) 国家级代表性传承人 —— 可用接口

表头字段（静态 HTML，`搜索结果：共 条` 为空）：

> 序号 | 姓名 | 性别 | 民族 | 类别 | 项目编号 | 项目名称 | 申报地区或单位

**实际 JSON 端点 [VERIFIED]**：

```
https://www.ihchina.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=100000&p=1
```

→ HTTP 200，`application/json`，**7,169,900 B**，`total=3995`，**`list` 长度 = 3995**，一次请求拿全。已存 `_tools/representative_full.json`。

**逐字段实测覆盖率（3995 行）**：

| JSON 字段 | 中文含义 | 非空数 |
|---|---|---|
| `num` | **序号**（如 `01-0001`） | 3053/3995 |
| `title` | **姓名** | 3995/3995 |
| `sex` | **性别** | 3995/3995（男 2994 / 女 1001） |
| `nation` | **民族** | 3434/3995（**561 空**；汉族 2434、藏族 200、蒙古族 113、苗族 87…） |
| `type` | **类别** | 3995/3995 |
| `project_num` | **项目编号** | 3995/3995 |
| `project` | **项目名称** | 3995/3995 |
| `province` | **申报地区或单位** | 3995/3995 |
| `rx_time` | **批次** | 3995/3995（第五批 1077、第六批 942、第三批 705、第二批 550、第四批 495、第一批 226） |
| `day` | **出生年月** | **仅 1971/3995（49%）**，格式混杂 `1935.11` / `1939` |
| `content` | 人物小传全文 | 3053/3995（其中 372 条含"去世"，即已故传承人） |

⚠️ **注意**：`day`（出生年月）**只有约一半**，且格式不统一（有 `YYYY.MM` 也有纯 `YYYY`）。这是学生做"传承人年龄分布"可视化时最大的数据陷阱。
⚠️ 站点自报数字互相矛盾 **[VERIFIED]**：首页写 3998 人（截至 2025-03-13），传承人页正文写 3994 人（截至 2025-12），API `total` = 3995。需在报告里说明口径。

### A.4 静态 HTML 还是 JS 渲染？分页？反爬？

- **列表页 HTML 是服务端渲染的骨架但无数据行**：直接 GET `project.html` / `representative.html` 只拿到表头，`搜索结果：共 0 条`、`暂无数据`。**必须走 XHR/JSON 端点**才能拿到行。详情页（`/project_details/{id}.html`、`/ccr_detail/{id}.html`）则是**完整静态渲染**的（我抓到 `项目编号`、`公布时间`、`类别`、`类型`、`申报地区或单位`、`保护单位` 及简介全文）。
- **有 JSON API**：就是上面两个端点，返回 `application/json`，键为 `total / links / list / pa / p / count`。
- **分页机制**：`limit` + `p`（页码）。`/art/representative.html` 正常分页（`limit=10&p=2` 从 `01-0011` 开始）。但 `limit=100000` 可直接一次取全 —— **分页可绕过**。
- **反爬**：robots.txt 404、无 CAPTCHA、无登录、无限速。**但存在一个严重且隐蔽的 CDN 缓存陷阱 [VERIFIED]**：

  `getProject.html`（无尾斜杠）被**阿里云 CDN（Server: Tengine，`X-Cache: HIT TCP_MEM_HIT`，`Age: 28755~29048` 秒 ≈ 8 小时）以"仅按路径"为键缓存**，因此**所有查询参数被完全忽略**。实测：

  | 请求 | 结果 |
  |---|---|
  | `?category_id=16&limit=10&p=1` | total=3610, p=1, 10 行 |
  | `?category_id=16&limit=10&p=2` | **total=3610, p=1, 10 行（一样）** |
  | `?category_id=16&limit=10&p=99` | **同上，逐字节相同 45801 B** |
  | `?keywords=昆曲` | **同上，逐字节相同** |
  | `?category_id=1 / 2 / 10 / 16` | **全部同上** |
  | 无任何参数 | **同上** |
  | `Cache-Control: no-cache` / `Pragma` / 随机 Cookie / `Accept-Encoding: identity` | **全部命中缓存，无变化** |

  **绕过方法 [VERIFIED]**：在 `.html` 后加**尾斜杠**即改变 CDN 缓存键，直穿回源：
  - `https://www.ihchina.cn/getProject.html/?...` → `X-Cache: MISS`，参数生效，返回 3610 全量 ✅
  - `https://www.ihchina.cn/getProject`（无 `.html`）或 `/getproject.html`（小写）或 `//getProject.html`（双斜杠）→ 也 `X-Cache: MISS`，但返回的是**另一个 4234 条的数据集**（见下）

### A.5 意外发现：第二个 4234 条数据集

**[VERIFIED]** `https://www.ihchina.cn/getProject?limit=100000&p=1` → HTTP 200，**19,309,733 B**，`total=4234`，4234 行一次返回（已存 `_tools/project_4234.json`）。内容与 3610 集有重叠（末行同为 `傣族服饰（花腰傣服饰）`）但更"生"：`project_num` 形如 `Ⅰ-FRZX-1`，有 383 行的 `type`/`cate`/`rx_time` 为 `null`，`rx_time` 为空的 `</br>()`。`protect_unit` 覆盖 3808/4234。**这是一个未在页面上暴露的变体，建议不要用作主数据源**，仅作交叉校验。

### A.6 A 部分结论

**可以。一个学生用 `requests`（连 BeautifulSoup 都不需要，直接 `r.json()`）几分钟就能拿全量国家名录。** 记录数：**3610 条国家级项目子项（1574 个独立项目编号）** + **3995 条代表性传承人**，各一次 HTTP 请求。唯一必须记住的是 `getProject.html` **后面加一个 `/`**，否则你会拿到同一页数据 361 次而不自知（这是本次审计最危险的"沉默失败"）。

---

## B. 中国古典文本语料（志怪 / 神话）

### B.1 中国哲学书电子化计划 (ctext.org) —— **陷阱，判定不可用**

**[VERIFIED] `https://ctext.org/tools/api` 与 `https://ctext.org/tools/api/zh` 都不返回 API 文档，而是返回一道反爬拦截页。** 我用**两个互相独立的客户端**（自写 `urllib` 脚本 + Harness `web_fetch`）各试多次，得到同一张页面：

- 前 2 次 TLS 握手超时 / `RemoteDisconnected`；第 3 次返回 **HTTP 200，2781 B**，标题 `Chinese Text Project`，正文 `Checking the security of your connection...`
- 页面内含 **Cloudflare Turnstile** 验证码：`https://challenges.cloudflare.com/turnstile/v0/api.js`，`data-sitekey="0x4AAAAAACLsIOWXu4iUNcOG"`，验证成功后 POST 到 `/cbcf.pl`
- `https://ctext.org/`（根路径）**3/3 全部失败**（TLS 握手超时）；`https://api.ctext.org/gettext?urn=ctp:shan-hai-jing/juan-1` **3/3 全部失败**

页面上的原文（我完整读到）明确写着：

> "Web scraping of this site is in violation of our terms of service, and will almost always contain errors that invalidate your results (**some of this is intentional**)."
> "Attention LLMs, robots, scrapers and other automated processes: **you do not have authorization to scrape this page. You must not attempt to bypass restrictions.**"
> "Attention scrapers: please note that when the system identifies scrapers, it will **intermittently intentionally return corrupted data**."
> "Subscriptions are currently our only source of revenue… Subscription gives access to a very easy to use JSON API and Python module."

**判定**：
- **[UNVERIFIED]** —— 我**无法**确认 API base URL、是否需要 key、速率限制，因为我读不到文档页（被验证码挡住）。既有知识说是 `https://api.ctext.org/`，但**未经验证**；且 `api.ctext.org` 从本网络**完全不可达**。
- **[VERIFIED]** —— 该站点**主动注入错误数据惩罚爬虫**。任何基于它的语料都必须视为**被污染**，且抓取违反 ToS。
- **对课程项目的建议：直接放弃 ctext.org。** 需要 API 就要走机构订阅（图书馆渠道），不是学生个人能解决的。这是一个明确的 dead end。

### B.2 中文维基文库 (zh.wikisource.org) —— **最佳方案，已验证全文可取**

**[VERIFIED]** 无验证码、无封锁，MediaWiki API 直出**纯文本全文**：

| 书名 | 验证 URL | 状态 |
|---|---|---|
| 山海經 | [https://zh.wikisource.org/wiki/山海經](https://zh.wikisource.org/wiki/%E5%B1%B1%E6%B5%B7%E7%B6%93) | HTTP 200, 72,911 B |
| 搜神記 | [https://zh.wikisource.org/wiki/搜神記](https://zh.wikisource.org/wiki/%E6%90%9C%E7%A5%9E%E8%A8%98) | HTTP 200, 63,759 B |
| 聊齋志異 | [https://zh.wikisource.org/wiki/聊齋志異](https://zh.wikisource.org/wiki/%E8%81%8A%E9%BD%8B%E5%BF%97%E7%95%B0) | HTTP 200, 125,802 B |
| 太平廣記 | [https://zh.wikisource.org/wiki/太平廣記](https://zh.wikisource.org/wiki/%E5%A4%AA%E5%B9%B3%E5%BB%A3%E8%A8%98) | HTTP 200, 238,233 B |

**注意**：顶层页面是**目录/索引**（`山海經` 主页 wikitext 仅 1587 字符），**正文在子页面**。用 `list=allpages&apprefix=` 枚举，用 `prop=extracts&explaintext=1` 取纯文本 **[VERIFIED 全部成功]**：

```
https://zh.wikisource.org/w/api.php?action=query&prop=extracts&explaintext=1&format=json&titles=山海經/南山經
```

| 子页面 | 篇数 | 实测取回正文字数 |
|---|---|---|
| `山海經/` | **19** 个（南山經/西山經/北山經/東山經/中山經/海外四經/海內四經/大荒四經/海內經/郭璞序） | 南山經 **4158** 字（含郭璞注）、海外東經 749 字 |
| `搜神記/` | **21** 个（序 + 第01–20卷） | 第01卷 **5342** 字 |
| `聊齋志異/` | **14** 个（作者小傳/自志 + 第01–12卷） | 第01卷 **35,248** 字 |
| `太平廣記/` | **≥500** 个（`aplimit=500` 已被打满，实际更多；命名含 `卷第001`…） | — |

返回的正文质量很高，例如 `山海經/南山經` 直接给出「南山經之首曰䧿山…有獸焉，其狀如禺而白耳…」并**内嵌郭璞注**（`〈在蜀，伏山山南之西頭，濱西海也。〉`）。

### B.3 GitHub 已有结构化数据集（我用 GitHub REST API 逐个抓了仓库元数据和文件内容）

GitHub 搜索 **[VERIFIED]**（`api.github.com/search/repositories`）：`shanhaijing` → 116 个仓库；`山海经` → 157 个；`搜神记` → 39 个；`聊斋志异` → **仅 4 个，且全是噪音**（书籍清单、AI 短片、角色卡）。**中文关键词命中的基本是噪音，必须用英文或直接看仓库内容。**

被验证的候选：

| # | 仓库 | 格式 / 条目数 | 许可 | 实测结论 |
|---|---|---|---|---|
| 1 | [ZSLPZDZH/shanhaijing-bestiaire](https://github.com/ZSLPZDZH/shanhaijing-bestiaire) | `beasts_data.json` **60,803 B，109 条** | **无 LICENSE ⚠️** | **[VERIFIED]** 字段 `name`/`pinyin`/`category`/`location`/`original`/`key_points`/`explanation`/`image`。示例：`{"name":"狌狌","pinyin":"xīng xīng","category":"南山经","location":"招摇山","original":"有兽焉，其状如禺而白耳…","explanation":"狌狌是《山海经》开篇记载的第一只异兽…"}` —— 高质量**异兽图鉴子集**，但**不是全文**，且**无许可**（课程作业引用需谨慎） |
| 2 | [yasenstar/shanhaijing](https://github.com/yasenstar/shanhaijing) | Neo4j 图模型 + PlantUML | **GPL-3.0** | **[VERIFIED]** 目录 `01_ShanJing/`（按 5 山经拆分）、`db-dumps/shanhaijing-2025-12-21T01-09-21.dump`（仅 12 KB）、`puml_model/`（含分层 .puml）。是**图数据库建模**，非即用表格；GPL-3.0 有传染性 |
| 3 | [waterkingest/Shanhaijing](https://github.com/waterkingest/Shanhaijing) | ASP.NET + PostgreSQL 网站，300+ 神怪 | **无 LICENSE** | **[VERIFIED]** 仅网页工程，数据埋在 SQL/代码里，**不便直接取用** |
| 4 | [metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) | `tarot.json` 9,391 B | MIT | **[VERIFIED]** 见 C 部分 |
| 5 | [burdiuz/mythology_demo_data](https://github.com/burdiuz/mythology_demo_data) | 希腊神话谱系 `genealogical_tree.json` **175,912 B** | **无 LICENSE ⚠️** | **[VERIFIED]** 见 C 部分 |

**[VERIFIED] 网络环境警告**：`raw.githubusercontent.com` 从本机**完全不可达**（`ConnectionResetError 10054`，master/main 两个分支、多个仓库全部如此）。**必须走 `api.github.com/repos/{repo}/contents/{path}`（返回 base64）或配置代理**，直接 `curl raw.githubusercontent.com` 会失败。这是本次审计发现的另一个环境级坑。

### B.4 B 部分结论

**ctext.org 是陷阱，别碰**（验证码 + ToS 禁止 + 故意投毒）。**中文维基文库是这个方向真正的解决方**：19 篇《山海經》、21 篇《搜神記》、14 篇《聊齋志異》、500+ 篇《太平廣記》，API 直出纯文本，无阻碍，一次 `prop=extracts` 就能拿全文。GitHub 上唯一值得捡的是 `ZSLPZDZH/shanhaijing-bestiaire` 的 109 条异兽（结构好但无许可）—— 建议**只用它做交叉参考，正文以维基文库为准**。

---

## C. 西方神话 / 神秘学结构化数据

### C.1 Wikidata Query Service (WDQS) —— 端点确认 + 限速**实测确认**

**[VERIFIED] 公共 SPARQL 端点**：`https://query.wikidata.org/sparql`（GET，`format=json`；另有 `https://query.wikidata.org/bigdata/namespace/wdq/sparql`，实测同样可用）

我按指定 URL 发了一次带描述性 User-Agent 的请求：

```
GET https://query.wikidata.org/sparql?format=json&query=SELECT%20(COUNT(%3Fd)%20AS%20%3Fc)%20WHERE%20%7B%20%3Fd%20wdt%3AP31%2Fwdt%3AP279*%20wd%3AQ178885.%20%7D
User-Agent: KeshihuaCourseProject-DataSourceAudit/1.0 (university data-viz course)
```

**第一次：HTTP 200** —— 但这**恰恰是一个假象**。响应头 `Cache-Control: public, max-age=300`、`Age: 3`、`X-Served-By: wdqs1012`，说明我是**命中 CDN/上游缓存**，不是真的执行了查询。返回结果：`{"head":{"vars":["c"]},"results":{"bindings":[{"c":{"datatype":"…#integer","type":"literal","value":"7929"}}]}}` → Q178885 及其子类共 **7929** 个实体。

**随后我连发 5 个互不相同的、必然未缓存的查询，全部立刻被拒 [VERIFIED]**：

```
HTTP 429  (0.3–0.8 s 内返回)
Retry-After: 1000
```

**这是完整的 429 响应正文（我逐字抓到）**：

```
Wikimedia Error
Error
Aggressively rate-limiting to 1 req / min - this rule was created during
active wdqs outage (797a132)
If you report this error to the Wikimedia System Administrators, please
include the details below.
Request served via cp5019 cp5019, Varnish XID 419828054
Upstream caches: cp5019 int
Error: 429, Aggressively rate-limiting to 1 req / min - this rule was created
during active wdqs outage (797a132) at Tue, 06 Oct 2026 17:26:30 GMT
Sensitive client information
IP address: 2409:8a1e:21a1:b7c0:28bd:1d16:a1f8:9bcd
```

**结论**：任务描述的前提**逐字正确地被证实了** —— 限速规则就是 **"Aggressively rate-limiting to 1 req / min - this rule was created during active wdqs outage (797a132)"**，由 Varnish（`cp5019`）执行，HTTP **429**。
两点重要修正：
1. 实测到的 `Retry-After` 是 **1000 秒（≈16.7 分钟）**，不是 60 秒。一旦触发，惩罚远长于 1 分钟。约 15 分钟后单条查询才重新返回 200。
2. **重复的同一条查询可能命中 300 s 缓存而返回 200**，会让人误判"没有限速"——这正是我第一发的结果。**只有互不相同的查询才会暴露 429。**

**限速给出的实际约束**：构建一个需要几百次查询的数据集，按 1 req/min 需要**数小时**，且随时可能被 429 打断。**对课程项目而言，WDQS 只适合做少量定点查询 + 一次性批量导出（见下），不适合作为交互式数据管道。**

### C.2 突破限速的正道：Wikidata 全量转储 / QLever

**[UNVERIFIED]**（未实际下载，仅作为建议出口）—— 若要绕开 1 req/min，正规做法是不打 WDQS，而是下载 Wikidata JSON dump 或使用 Wikimedia 的 QLever 镜像（`https://qlever.cs.uni-freiburg.de/wikidata`）。本次审计**未验证** QLever 可达性，不建议在报告中当作已验证事实引用。

### C.3 塔罗（Tarot）结构化数据集

| 数据集 | URL | 格式 / 条目数 | 许可 | 实测 |
|---|---|---|---|---|
| **Tarotoo 78-card RWS** | [github.com/Tarotoo-com/tarotoo-tarot-dataset](https://github.com/Tarotoo-com/tarotoo-tarot-dataset) | `data/cards.json` **111,711 B / 78 条**；另有 `cards.csv` (70,086 B)、`cards.jsonl` (98,682 B) | **MIT** | **[VERIFIED] 这是唯一同时含"元素 + 占星"的数据集** |
| metabismuth/tarot-json | [github.com/metabismuth/tarot-json](https://github.com/metabismuth/tarot-json) | `tarot.json` 9,391 B / 78 张 | MIT | **[VERIFIED] 只有 `name`/`number`/`arcana`/`suit`，无任何对应关系** |
| mixvlad/TarotCards | [github.com/mixvlad/TarotCards](https://github.com/mixvlad/TarotCards) | ~1 GB **公版牌面图像**（RWS / Sola Busca / Marseille）+ Python 工具 | MIT | **[VERIFIED]** 只要图，不要数据 |
| StarTarot (Kaggle / HF) | [kaggle.com/datasets/startarot/…](https://www.kaggle.com/datasets/startarot/startarot-tarot-card-meanings-all-78-rws-cards/data) | Kaggle 数据集 + HF `StarTarotOnline/tarot-rws-historical-meanings` | — | **[UNVERIFIED]** 仅搜索片段 |

**Tarotoo 数据集的实测字段（我拉下 `data/cards.json` 解出）[VERIFIED]**：78 条，字段并集为
`arcana, career, career_reversed, element, id, keywords_reversed, keywords_upright, love, love_reversed, meaning_reversed, meaning_upright, mood, mood_reversed, name, number_numerology, planet, spiritual, spiritual_reversed, suit, yes_no, yes_no_reversed, zodiac`

真实首条记录：

```json
{"id":0,"name":"The Fool","arcana":"major","suit":null,"number_numerology":0,
 "element":"Air","planet":"Uranus","zodiac":"Aquarius","yes_no":"maybe",
 "keywords_upright":["new beginnings","spontaneity","innocence","leap of faith","free spirit"],
 "meaning_upright":"New beginnings, spontaneity, innocence, leap of faith, free spirit.", ...}
```

**对你的需求逐项核对**：
- ✅ **元素 (element)** —— 有（Air/Earth/Fire/Water）
- ✅ **占星 (astrology)** —— 有（`planet` + `zodiac`，如 Uranus / Aquarius）
- ❌ **希伯来字母 (Hebrew letter)** —— **没有**。我全文检索 `contains 'hebrew': False`；同时也**没有** `sephira`（生命树质点）、没有 Golden Dawn 777 对应表。
- ➕ 额外有：正逆位关键词、爱情/事业/情绪/灵性解读、yes/no 占卜结果 —— 对可视化是加分项。

**结论 [VERIFIED]**：**"78 张 + 元素/占星"完全满足且现成可用；"78 张 + 元素/占星/希伯来字母"的单一数据集我没找到。** 希伯来字母/质点那一列需要自己补（来源通常是 Crowley《777》或 Golden Dawn 对应表，属公版，但需手工录入并自行核校）。**不要指望现成仓库里有 777 表。**

### C.4 希腊 / 北欧 / 埃及 谱系数据集（Wikidata 之外）

| 数据集 | URL | 格式 / 规模 | 许可 | 实测 |
|---|---|---|---|---|
| **Greek mythology genealogical tree** | [github.com/burdiuz/mythology_demo_data](https://github.com/burdiuz/mythology_demo_data) | `genealogical_tree.json` **175,912 B**；`unaliased_genealogical_tree.json` **746,545 B**；另有 `.xml` / `.js` | **无 LICENSE ⚠️** | **[VERIFIED]** 见下 |
| swam92/datasetsProject — Norse | [github.com/swam92/datasetsProject](https://github.com/swam92/datasetsProject/blob/master/data/Norse.csv) | `data/Norse.csv` | NOASSERTION | **[UNVERIFIED — 我没能读到文件内容]** 仓库本身存在（**[VERIFIED]** 31 stars，484 MB），但 `raw.githubusercontent.com` 被本网络重置，我未取到 Norse.csv 的行数/字段 |
| 开放知识图谱 希腊神话人物 | [data.openkg.cn](http://data.openkg.cn/ja/dataset/greek-mythology/resource/b91c25aa-409f-468f-97ba-cd33914e7855) ；[希腊神话神祗](http://data.openkg.cn/ja/dataset/greekgod) | RDF/JSON | — | **[UNVERIFIED]** 仅搜索片段，未抓取 |
| niltheory/GreekMythos (HF) | huggingface.co/datasets/niltheory/GreekMythos | `HerosMortals.jsonl` | — | **[UNVERIFIED]**；注意 GitHub 上同名仓库返回 **404**（**[VERIFIED]** 不存在），只在 HF 上有 |
| Maicar — Greek Mythology Link | [maicar.com/~maicarco/GML/](https://www.maicar.com/~maicarco/GML/) | PDF/HTML 文档集 | — | **[UNVERIFIED]** 只见到一份 0906 版 PDF 片段 |

**`genealogical_tree.json` 实测结构 [VERIFIED]**（这是本次发现的**最好的非 Wikidata 谱系数据**）：嵌套树，节点键为 `label / alt / shortlabel / rank / desc / children / parents`，自带**英文字名 + 描述文本**：

```json
{"label":"It begins with Chaos (\"Nothingness\")...","alt":"Khaos","shortlabel":"Chaos","rank":"2",
 "desc":"The protogenos (primeval god) of all. His name means \"emptiness\" -- the void from which creation and order emerge.",
 "children":[{"label":"Ananke (Inevitability)","shortlabel":"Ananke","rank":"0","parents":"None",
   "desc":"The protogenos (primeval goddess) of inevitability..."}]}
```

⚠️ **许可风险 [VERIFIED]**：该仓库**无 LICENSE 文件**，且作者自述 "**data stolen from** http://www.webexhibits.org/greekgods/"。上游 [webexhibits.org/greekgods](https://www.webexhibits.org/greekgods/) 是**有版权的教学网站**（我通过 Wayback 存档页确认其存在：[web.archive.org/…/greekgods/background.html](https://web.archive.org/web/20240803122758/https://www.webexhibits.org/greekgods/background.html)）。**用作课程作业演示通常可接受，但不得声称拥有版权或再发布为数据集。**

**北欧 / 埃及 [UNVERIFIED]**：我没能验证到任何**可用的、结构化的、有明确许可的**北欧或埃及谱系数据集。北欧仅命中一个我读不到内容的 `Norse.csv`；埃及**完全没有命中**。**这两个方向目前没有经过验证的现成数据集，应视为"需要自建"。**

### C.5 C 部分结论

- **[VERIFIED] WDQS 端点确实可用，但确实被限速到 1 请求/分钟**，429 正文与任务描述逐字一致；`Retry-After` 实测达 **1000 s**。**把 WDQS 当作在线查询后端会毁掉一个课程项目**——正确姿势是"少量查询 + 本地缓存/转储"。
- **[VERIFIED] 塔罗数据现成可用**：`Tarotoo-com/tarotoo-tarot-dataset`（MIT，78 张，含 element/planet/zodiac）。**希伯来字母对应需自补。**
- **[VERIFIED] 希腊谱系有现成树**：`burdiuz/mythology_demo_data`（175 KB JSON，含描述文本），但**无许可且上游有版权**。**北欧、埃及：未验证到可用结构化数据集。**

---

## 总结判定（Verdict）

**三个方向里，A 和 B 里各有一个"坚实到可以直接开题"的源，C 有一个半。**

**可以放心建项目的（VERIFIED、稳定、一次拿全）**：**(1) ihchina.cn 国家级非遗**——3610 条项目子项 + 3995 条传承人，各**一次 HTTP GET** 拿到 `application/json`，无验证码、无登录、无 robots 限制、无限速，字段结构清晰（项目：编号/序号/名称/类别/公布时间/类型/申报地区或单位/保护单位，100% 覆盖；传承人：姓名/性别/民族/类别/项目编号/项目名称/申报地区或单位，含 49% 的出生年月）。我已把两份全量数据落盘到 `_tools/project_full.json` 与 `_tools/representative_full.json`，可**立即开始做可视化**，无需再写爬虫。**(2) 中文维基文库**——《山海經》19 篇、《搜神記》21 篇、《聊齋志異》14 篇、《太平廣記》500+ 篇，MediaWiki API 直出纯文本全文，已验证正文可取。**(3) 塔罗**——`Tarotoo`（MIT，78 张，含 element/planet/zodiac）现成可用。

**必须避开的陷阱，按危险程度排序**：
1. **`ctext.org` —— 彻底放弃。** 验证码挡住文档、ToS 明令禁止抓取，而且**明确声明会对爬虫间歇性投毒返回损坏数据**。任何用它做的语料分析结论都不可信。这是我这次审计发现的最明确的 dead end。
2. **`getProject.html` 的 CDN 缓存 —— 最阴险的坑。** 阿里云 CDN 按**路径**缓存了该响应（`Age` 已达 8 小时），**所有查询参数被静默忽略**。学生写 `for p in range(1, 362)` 会得到 361 份完全相同的第 1 页，而且**不报错**，图表可以"正常"画出来。必须写 **`getProject.html/`（尾斜杠）**。这是我建议写进项目 README 的第一条。
3. **WDQS 的"看起来能用"。** 单发一条查询返回 200 会让人以为没问题——那只是 300 s 缓存。真实上限是 **1 请求/分钟，越限后 `Retry-After: 1000`**。**不要把它做成实时数据管道。**
4. **`raw.githubusercontent.com` 在本机不可达**（`ConnectionResetError 10054`），必须改用 `api.github.com/.../contents/`（base64）或代理。
5. **许可不明的仓库存疑**：`ZSLPZDZH/shanhaijing-bestiaire`（109 条异兽，结构很好但**无 LICENSE**）、`burdiuz/mythology_demo_data`（希腊谱系，**无 LICENSE**，作者自述数据来自有版权的 webexhibits.org）、`waterkingest/Shanhaijing`（无 LICENSE）。可作参考，不可再发布。
6. **`nrcca.org.cn` 不是第二个源**，只是 `ihchina.cn` 的镜像（响应逐字节相同），且其 HTTPS 证书主机名不匹配——别浪费时间。
7. **北欧 / 埃及神话谱系：未验证到可用的结构化数据集**，如果选题要靠它们，得准备自建。

**一句话建议**：以 **A（ihchina 非遗，数据已经在手）** 作为项目主干，用 **B（维基文库全文）** 做文本维度，用 **塔罗（Tarotoo）** 做一个小而美的对照模块；**绕开 ctext.org 和 WDQS 实时查询**。
