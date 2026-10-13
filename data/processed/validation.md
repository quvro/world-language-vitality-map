# 数据校验报告

## 规模

- WALS values: 76,475 行
- WALS languages: 3,573 行
- dim_language: 3,573 行（主键 wals_id），有经纬度 2,662
- 其中**真语言** 2,662 行；另 911 行是语系/语族/语支层级占位（family 254、genus 625、subfamily 32），导出给前端的 languages.json 已剔除
- fact_language_feature: 76,475 行，覆盖语言 2,660，覆盖特征 192
- feature_vector: 2,660 × 192，填充率 15.0%
- 时间序列: 66,103 行
- 可关联 WALS 的维基版本: 271

## 标识符模型（重要）

- WALS `ID` 唯一：3,573 个 → **主键**
- `Glottocode` 不唯一：2,502 个，其中 93 个对应多个 WALS 变体
- 受影响变体记录：236 条

WALS 的 Glottocode 指向「语言」层级，而 WALS 的分析单元是「变体」。
例如 `swis1247` 同时是阿尔萨斯语与 5 种瑞士德语，特征取值互相冲突。
以 Glottocode 作主键会静默合并这些变体并丢失数据，故改用 `wals_id`。

变体最多的 Glottocode：

| Glottocode | 变体数 | 成员 |
|---|---|---|
| `basq1248` | 11 | Basque (Bidasoa Vall、Basque (Gernica)、Basque (Hondarribia)、Basque (Basaburua an … |
| `swis1247` | 6 | Alsatian、German (Bern)、German (Ostschweiz)、German (Appenzell) … |
| `stan1295` | 6 | German (Berlin)、German、German (Hannover)、German (Mansfeldisch … |
| `stra1244` | 6 | Lummi、Saanich、Songish、Sooke … |
| `tibe1272` | 6 | Rang Pas、Tibetan (Dingri)、Tibetan (Drokpa)、Tibetan (Standard Sp … |
| `nort3139` | 4 | Arabic (Beirut)、Arabic (North Levant、Arabic (Lebanese)、Arabic (Syrian) |
| `band1339` | 4 | Bandjalang (Casino)、Bandjalang、Bandjalang (Waalubal、Bandjalang (Yugumbir |
| `cari1279` | 4 | Carijona、Guaque、Hianacoto、Umaua |

## 维基关联的歧义（必须知道）

- 成功关联的维基版本：271
- 其中 ISO 码对应多个 WALS 条目的：**263**（97%）

这不是数据错误，而是两个体系的粒度差异：**ISO 639-3 标识「语言」，
WALS 收录的是「变体」**。例如维基的 `de` 对应 ISO `deu`，
而 WALS 下 `stan1295` 有 6 条变体记录（标准德语、伯尔尼德语、苏黎世德语…）。

处理方式：**按特征数据最丰富者择优**（并列时按 `wals_id` 取值，保证确定性），
并在 `dim_wiki_edition.join_ambiguous` 与 `iso_candidates` 中显式记录，
便于答辩时说明与复核。

## 语系分布（Top 15）

- (空): 911
- Niger-Congo: 324
- Austronesian: 324
- Indo-European: 176
- Sino-Tibetan: 146
- Afro-Asiatic: 145
- Pama-Nyungan: 121
- Trans-New Guinea: 98
- other: 72
- Altaic: 65
- Oto-Manguean: 56
- Austro-Asiatic: 48
- Eastern Sudanic: 47
- Uto-Aztecan: 44
- Algic: 31

## 主要语区分布

- (空): 911
- Eurasia: 659
- Africa: 606
- Papunesia: 560
- North America: 396
- South America: 258
- Australia: 183

## 特征覆盖率（决定条件对比交互能用哪些特征）

- 特征总数: 192
- 每特征覆盖语言数：中位数 257，最少 5，最多 1518
- 覆盖 ≥ 300 个语言的特征: 88 个

| 覆盖最好的 8 个特征 | 语言数 |
|---|---|
| Order of Object and Verb | 1,518 |
| Order of Subject and Verb | 1,496 |
| Order of Subject, Object and Verb | 1,376 |
| Order of Adjective and Noun | 1,367 |
| Order of Negative Morpheme and Verb | 1,325 |
| Minor morphological means of signaling negation | 1,325 |
| Postverbal Negative Morphemes | 1,325 |
| Preverbal Negative Morphemes | 1,325 |

## 活力增长最快 / 最慢（仅基线可靠的语言）

基线门槛：首 3 个月月均浏览量 ≥ 10,000。
低于门槛的维基多为「早期未被统计、后来才开始记录」，
其增长率是统计伪影而非真实增长，已排除。

| 语言 | 首 3 月均值 | 末 3 月均值 | 增长 |
|---|---|---|---|
| Tagalog | 8,354,185 | 1,738,906 | -79.2% |
| Spanish | 1,097,343,011 | 504,362,838 | -54.0% |
| Sorbian | 271,571 | 138,514 | -49.0% |
| Indonesian | 77,699,577 | 40,697,790 | -47.6% |
| Portuguese | 332,374,429 | 181,404,379 | -45.4% |
| Pipil | 64,098 | 35,465 | -44.7% |
| Ilocano | 353,207 | 216,399 | -38.7% |
| Kazakh | 5,409,960 | 3,401,274 | -37.1% |
| Dinka | 69,145 | 44,401 | -35.8% |
| Russian | 844,764,449 | 554,313,586 | -34.4% |
| Meithei | 30,493 | 650,018 | +2031.7% |
| Cheyenne | 47,325 | 1,026,114 | +2068.2% |
| Dagbani | 15,728 | 384,888 | +2347.1% |
| Tashlhiyt | 27,930 | 721,933 | +2484.8% |
| Akan | 35,123 | 1,156,272 | +3192.0% |
| Hausa | 73,034 | 2,868,657 | +3827.8% |
| Cree (Plains) | 24,325 | 1,045,994 | +4200.1% |
| Iñupiaq | 30,952 | 1,337,518 | +4221.2% |
| Fijian | 31,685 | 2,039,312 | +6336.1% |
| Seediq | 13,761 | 1,427,131 | +10270.6% |

## 被排除的疑似统计伪影（示例）

| 语言 | 首 3 月均值 | 末 3 月均值 | 表观增长 |
|---|---|---|---|
| Amis | 5,886 | 87,830 | +1,392% |
| Nigerian Pidgin | 9,812 | 138,371 | +1,310% |
| Herero | 5,916 | 40,961 | +592% |
| Nupe | 8,694 | 56,628 | +551% |
| Kanuri | 9,033 | 57,655 | +538% |
| Marshallese | 5,591 | 27,882 | +399% |
| Seminole | 5,992 | 27,490 | +359% |
| Paiwan | 6,933 | 29,335 | +323% |