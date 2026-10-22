# `_tools/` 脚本的阶段归属

**这个目录混了两条路线的产物，先看这张表再读代码，否则会被误导。**

项目中途换过选题。下面「已放弃方向」里的东西与最终的
《世界语言赛博活力图谱》**没有任何关系**，保留它们只是为了留痕备查
（也记录了当时是怎么判断某个数据源不可用的）。

---

## A. 最终项目（世界语言赛博活力图谱）相关 —— 有参考价值

| 文件 | 干了什么 | 结论 / 影响 |
|---|---|---|
| `probe_join.py` | 探 WALS（语言结构）能不能和 Wikimedia（时间序列）关联 | 项目的可行性前提，成立 |
| `probe_join2.py` | 用 ISO 639-1 → 639-3 映射，摸清真实的关联规模 | 关联数从 116 提到 247 的关键一步 |
| `probe_wals_blob.py` | 本机 `github.com` / `raw.githubusercontent.com` 不可达时，改用 `api.github.com` 的 blob API 取 WALS CSV | 成了管道 01 的实际取数方式 |
| `probe_macro_members.py` | Wikidata 是否把宏观语言的 ISO 码与成员变体码连起来 | 是 → 后来做了「宏观语言回退」这一跳 |
| `probe_macro_precision.py` | 对比 `P279` 与 `P279+` 的精确度 | **`P279+` 的传递闭包会把 `ar → mlt`（马耳他语）也算进来**，所以最后用单层 `P279` |
| `probe_glottolog_macro.py` | Glottolog 的分类能否解析宏观语言 | 备选方案，最终用的是 Wikidata `P279` |
| `probe_dimension.py` | 给 WALS 找一个可对比的时间/第二维度 | 选定 Wikimedia 时间序列 |
| `diag_dupes.py` | 诊断 WALS `languages.csv` 里重复的 Glottocode | 支撑「主键用 `wals_id` 而非 `glottocode`」这个决定 |
| `probe_feature_matrix.py` | M4「记录缺口图」的可行性：稀疏度、双重缺席、特征蕴含 | 直接产出了那个视图的三个结论 |
| `extract_refs.py` | 把老师给的参考 PPTX / DOCX 抽成纯文本 | 需求对齐用。改为命令行传参 |
| `audit_current_data.py` | **数据不变量审查**：重算活力指标、校验坐标/语区/关联/濒危等级 | 抓到「一个 WALS 条目被多个维基版本认领」那个真 bug |
| `list_db.py` | 列出 SQLite 全部表与行数，抽查濒危等级 | 日常核对用 |
| `latest_numbers.py` | 产出 README 要引用的最新数字 | 避免文档数字过期 |

## B. 已放弃方向（民俗 / 神话 / 非遗 / 神秘学）—— **已移出本仓库**

> ⚠️ 下面这些脚本与输出**已经从版本库移除**（作者本地仍保留）。
> 原因：属于中途换掉的选题方向、与本项目无关，
> 且多个脚本里硬编码了本地绝对路径，不适合放进公开仓库。
>
> **`DATA_SOURCE_AUDIT.md` 保留在仓库里** —— 它是当时的数据源可行性审计报告，
> 记录了不少真实的踩坑（尤其 ctext.org 那条），对"为什么换选题"有交代价值。

| 文件（已移出） | 干了什么 |
|---|---|
| `audit_a*.py`（7 个） | 中国非物质文化遗产（ihchina.cn）接口与反爬探测 |
| `audit_b*.py`、`audit_bc.py` | 中国古典文本语料（ctext.org / 维基文库）探测 |
| `audit_c*.py`、`audit_c_wdqs.py` | 西方神话 / 神秘学的 Wikidata 探测 |
| `audit_final*.py`、`audit_integrity.py` | 上述审计的收尾与自洽性检查 |
| `probe_shanhaijing.py`、`extract_shanhaijing.py` | 《山海经》文本抽取原型 |
| `probe_wikidata.py`、`probe_wikidata2.py`、`probe_wikidataB.py`、`probe_wikidataB3.py` | 神祇 / 神话实体的 Wikidata 覆盖度探测 |
| `verify_ihchina.py` | 独立复核 ihchina 数据集 |
| `probe_candidates*.py`（3 个） | 更早一轮的选题候选探测（经济类、博物馆类 API） |
| `results_*.txt`（8 个） | 上面这些脚本的控制台输出存档（内容是 ctext.org / ihchina.cn 之类） |

> 顺带留下一条有用的结论：**ctext.org 是陷阱**（CAPTCHA + ToS 限制 + 数据投毒），
> 这条路当时判定不可用，记录在 `DATA_SOURCE_AUDIT.md` 的 B.1 节。
