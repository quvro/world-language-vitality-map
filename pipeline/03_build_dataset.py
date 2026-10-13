# -*- coding: utf-8 -*-
"""Step 03 - build the SQLite database and the frontend-facing JSON.

Key modelling decision (corrected after measuring the data):
    WALS's ``ID`` is the unique unit of analysis (3,573 distinct values).
    ``Glottocode`` is NOT unique: 3,573 rows share only 2,502 Glottocodes, and
    93 Glottocodes cover 2-6 genuinely different varieties (swis1247 alone is
    Alsatian + 5 Swiss German varieties) whose feature values conflict in
    90 of 93 cases. Keying on Glottocode silently merged those varieties.
    So: primary key = wals_id; glottocode is a non-unique grouping key that
    lets us roll up to the language level and attach dialect data later.

Other decisions honoured here (design doc §10):
    * feature_vector is materialised wide (192 cols) so "find languages by
      feature" and the conditional-comparison interaction need no runtime pivot
    * the wide table's blanks mean "WALS does not cover this", not "absent"

Outputs:
    data/processed/language_vitality.db
    data/processed/languages.json       metadata for the map
    data/processed/timeseries.json      per-language monthly views/edits
    data/processed/features.json        feature + code definitions
    data/processed/feature_matrix.json  the wide feature matrix
    data/processed/validation.md        data quality report
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    PROCESSED, WALS_DIR, WIKIMEDIA_DIR, XREF_DIR, banner, human, log, norm_month,
    read_json, records, write_json,
)

DB = os.path.join(PROCESSED, "language_vitality.db")
BASELINE_MIN = 10_000


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(WALS_DIR, name), dtype=str,
                       keep_default_na=False)


def main() -> None:
    banner("1. 读取原始数据")
    values = load_csv("values.csv")
    languages = load_csv("languages.csv")
    parameters = load_csv("parameters.csv")
    codes = load_csv("codes.csv")
    genealogy = load_csv("genealogy.csv")
    log(f"  values      {human(len(values))} 行")
    log(f"  languages   {human(len(languages))} 行")
    log(f"  parameters  {human(len(parameters))} 行")
    log(f"  codes       {human(len(codes))} 行")

    join = read_json(os.path.join(WIKIMEDIA_DIR, "join.json"))
    pv_path = os.path.join(WIKIMEDIA_DIR, "pageviews.json")
    ed_path = os.path.join(WIKIMEDIA_DIR, "edits.json")
    pageviews = read_json(pv_path) if os.path.exists(pv_path) else {}
    edits = read_json(ed_path) if os.path.exists(ed_path) else {}
    iso1_to_3 = read_json(os.path.join(XREF_DIR, "iso639.json"))
    log(f"  维基关联    {human(len(join))} 行")
    log(f"  浏览量数据  {human(sum(1 for v in pageviews.values() if v))} 个版本")

    # ---------------------------------------------------------------- dim_language
    banner("2. 构建 dim_language（主键 = wals_id，glottocode 为分组键）")
    dim_language = languages[[
        "ID", "Name", "Macroarea", "Latitude", "Longitude", "Glottocode",
        "ISO639P3code", "Family", "Subfamily", "Genus", "Country_ID",
    ]].rename(columns={
        "ID": "wals_id", "Name": "name", "Macroarea": "macroarea",
        "Latitude": "latitude", "Longitude": "longitude",
        "Glottocode": "glottocode", "ISO639P3code": "iso639p3",
        "Family": "family", "Subfamily": "subfamily", "Genus": "genus",
        "Country_ID": "country_id",
    })
    dim_language["latitude"] = pd.to_numeric(dim_language["latitude"], errors="coerce")
    dim_language["longitude"] = pd.to_numeric(dim_language["longitude"], errors="coerce")
    dim_language["glottocode"] = dim_language["glottocode"].replace("", None)

    # WALS 的 languages.csv 里**混有语系 / 语族 / 语支的层级占位行**
    # （ID 形如 family-abun、genus-berber、subfamily-chadic），它们不是语言。
    # 实测 3,573 行里只有 2,662 行是真语言。不区分的话后果很实际：
    #   · 顶栏「语言数」虚高约 900
    #   · 这些行的 Family 为空，于是语系筛选里多出一个巨大的「未分类」桶
    #   · 搜 "Chadic" 会搜出语系占位行
    # 所以 dim_language 保留全部原始行并标 kind，导出给前端时再剔除。
    def _kind(wid: str) -> str:
        for p in ("family-", "subfamily-", "genus-"):
            if wid.startswith(p):
                return p.rstrip("-")
        return "language"

    dim_language["kind"] = dim_language["wals_id"].map(_kind)
    kinds = Counter(dim_language["kind"])
    log("  行类型        = " + "  ".join(f"{k}={human(v)}" for k, v in kinds.most_common()))
    log(f"    -> 真语言 {human(kinds['language'])} 行；"
        f"另 {human(len(dim_language) - kinds['language'])} 行是层级占位，导出时剔除")

    has_coords = int(dim_language[["latitude", "longitude"]].notna().all(axis=1).sum())
    log(f"  wals_id 唯一  = {dim_language['wals_id'].is_unique}")
    log(f"  有经纬度      = {human(has_coords)} / {human(len(dim_language))}")
    g_counts = dim_language["glottocode"].dropna().value_counts()
    multi = g_counts[g_counts > 1]
    log(f"  glottocode 数 = {human(int(dim_language['glottocode'].nunique()))}，"
        f"其中 {human(len(multi))} 个对应多个 WALS 变体")
    log(f"    -> 这 {human(int(multi.sum()))} 条变体记录被完整保留（旧版会被合并丢失）")

    # ------------------------------------------------------- fact_language_feature
    banner("3. 构建 fact_language_feature")
    feat = values[["Language_ID", "Parameter_ID", "Value", "Code_ID"]].copy()
    feat = feat.rename(columns={
        "Language_ID": "wals_id", "Parameter_ID": "feature_id",
        "Value": "value_raw", "Code_ID": "code_id"})
    known = set(dim_language["wals_id"])
    orphan = (~feat["wals_id"].isin(known)).sum()
    log(f"  无法对应到 dim_language 的记录 = {human(int(orphan))}")
    feat = feat[feat["wals_id"].isin(known)]
    dup_before = len(feat)
    feat = feat.drop_duplicates(subset=["wals_id", "feature_id"])
    log(f"  重复 (语言,特征) 对已去重 = {human(dup_before - len(feat))}")
    log(f"  最终 = {human(len(feat))} 行；覆盖语言 "
        f"{human(feat['wals_id'].nunique())}，覆盖特征 "
        f"{human(feat['feature_id'].nunique())}")

    # ------------------------------------------------------------------- wide table
    banner("4. 物化 feature_vector 宽表（192 列）")
    wide = feat.pivot_table(index="wals_id", columns="feature_id",
                            values="value_raw", aggfunc="first")
    feature_ids = sorted(parameters["ID"].tolist())
    for fid in feature_ids:
        if fid not in wide.columns:
            wide[fid] = pd.NA
    wide = wide[feature_ids].reindex(sorted(wide.index))
    filled = int(wide.notna().sum().sum())
    total_cells = wide.shape[0] * wide.shape[1]
    log(f"  矩阵 = {human(wide.shape[0])} 语言 x {human(wide.shape[1])} 特征")
    log(f"  填充率 = {filled / total_cells * 100:.1f}%  "
        f"（空白含义是「WALS 未收录」）")

    # ------------------------------------------------------ fact_language_timeseries
    banner("5. 构建 fact_language_timeseries")
    ts_rows = []
    for code, meta in join.items():
        if not meta.get("joined") or not meta.get("wals_id"):
            continue
        for metric, store in (("views", pageviews), ("edits", edits)):
            for month, val in (store.get(code) or {}).items():
                ts_rows.append({"wals_id": meta["wals_id"], "wiki_code": code,
                                "month": norm_month(month), "metric": metric,
                                "value": val})
    timeseries = pd.DataFrame(ts_rows)
    log(f"  时间序列行数 = {human(len(timeseries))}")
    if len(timeseries):
        log(f"  覆盖语言 = {human(timeseries['wals_id'].nunique())}")
        log(f"  月份范围 = {timeseries['month'].min()} .. {timeseries['month'].max()}")
        bad = timeseries[~timeseries["month"].str.match(r"^\d{6}$")]
        if len(bad):
            log(f"  !! 月份键非法 = {human(len(bad))} 行，样例 "
                f"{sorted(bad['month'].unique())[:5]}")
            log("     -> 请重跑 02_fetch_wikimedia.py")
        else:
            log("  月份键格式检查：全部通过 (YYYYMM)")

    # ------------------------------------------------------------------- sqlite
    banner("6. 写入 SQLite")
    # ⚠️ 这里曾经是 `os.remove(DB)` 直接删库重建 —— 那会把 **05/06 写进同一张库的
    #    dim_endangerment 表静默清掉**（本次 review 就踩到了：重跑 03 之后
    #    「濒危 × 关注」的数据在库里消失，而磁盘上的 JSON 还在，所以从界面上看不出来）。
    #    改成只重建本步骤负责的表，其余表原样保留。
    OWNED_TABLES = (
        "dim_language", "dim_feature", "dim_code", "fact_language_feature",
        "fact_language_timeseries", "dim_genealogy", "dim_wiki_edition",
        "xref_iso", "feature_vector",
    )
    con = sqlite3.connect(DB)
    kept = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")]
    for tbl in OWNED_TABLES:
        con.execute(f'DROP TABLE IF EXISTS "{tbl}"')
    surviving = [t for t in kept if t not in OWNED_TABLES]
    if surviving:
        log(f"  保留其他步骤写入的表：{', '.join(sorted(surviving))}")

    dim_language.to_sql("dim_language", con, index=False)
    parameters.rename(columns={
        "ID": "feature_id", "Name": "name", "Description": "description",
        "Chapter_ID": "chapter_id"}).to_sql("dim_feature", con, index=False)
    codes.rename(columns={
        "ID": "code_id", "Parameter_ID": "feature_id", "Name": "name",
        "Description": "description", "Number": "number"}).to_sql(
        "dim_code", con, index=False)
    feat.to_sql("fact_language_feature", con, index=False)
    if len(timeseries):
        timeseries.to_sql("fact_language_timeseries", con, index=False)
    genealogy.to_sql("dim_genealogy", con, index=False)
    pd.DataFrame([{"wiki_code": k, **v} for k, v in join.items()]).to_sql(
        "dim_wiki_edition", con, index=False)
    pd.DataFrame([{"iso1": k, "iso3": v} for k, v in iso1_to_3.items()]).to_sql(
        "xref_iso", con, index=False)
    wide.reset_index().to_sql("feature_vector", con, index=False)

    for tbl, cols in (
        ("fact_language_feature", ("wals_id", "feature_id")),
        ("fact_language_timeseries", ("wals_id", "month")),
        ("dim_language", ("glottocode", "family", "macroarea")),
    ):
        for c in cols:
            con.execute(f'CREATE INDEX ix_{tbl}_{c} ON "{tbl}"({c})')
    con.commit()
    tables = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table' order by name")]
    log(f"  表：{tables}")
    con.close()
    log(f"  数据库大小 = {human(os.path.getsize(DB))} B")

    # ------------------------------------------------------------------- json
    banner("7. 导出前端 JSON")
    # records() turns NaN into None: pandas NaN would be written as bare `NaN`,
    # which JSON.parse rejects, blanking the whole page.
    # 只在导出这一层剔除语系/语族占位行；SQLite 的 dim_language 保留全部原始行。
    real = dim_language[dim_language["kind"] == "language"]
    langs = records(real)
    log(f"  剔除层级占位行 {human(len(dim_language) - len(real))} 条，"
        f"保留真语言 {human(len(langs))} 条")
    wiki_of = {m["wals_id"]: c for c, m in join.items()
               if m.get("joined") and m.get("wals_id")}
    for rec in langs:
        rec["wiki_code"] = wiki_of.get(rec["wals_id"])

    # vitality: 3-month means on both ends; a low baseline means the wiki only
    # "started being measured" later, which is an artefact, not growth.
    vitality: dict[str, dict] = {}
    if len(timeseries):
        v = timeseries[timeseries["metric"] == "views"]
        for wid, grp in v.groupby("wals_id"):
            grp = grp.sort_values("month")
            if len(grp) < 6:
                continue
            base = float(grp.head(3)["value"].mean())
            recent = float(grp.tail(3)["value"].mean())
            rec = {
                "month_first": grp.iloc[0]["month"],
                "views_first": int(grp.iloc[0]["value"]),
                "month_last": grp.iloc[-1]["month"],
                "views_last": int(grp.iloc[-1]["value"]),
                "views_baseline": round(base, 1),
                "views_recent": round(recent, 1),
                "baseline_ok": bool(base >= BASELINE_MIN),
            }
            if base > 0:
                rec["growth"] = round((recent - base) / base, 4)
            vitality[wid] = rec
    for rec in langs:
        rec.update(vitality.get(rec["wals_id"], {}))
    reliable = {k: s for k, s in vitality.items()
                if s.get("baseline_ok") and s.get("growth") is not None}
    log(f"  活力指标：{human(len(vitality))} 个语言有序列，"
        f"其中 {human(len(reliable))} 个基线可靠（门槛 {human(BASELINE_MIN)}）")

    write_json(os.path.join(PROCESSED, "languages.json"), langs)
    log(f"  languages.json      {human(len(langs))} 条")

    write_json(os.path.join(PROCESSED, "timeseries.json"), {
        "metrics": ["views", "edits"],
        "by_language": {
            wid: {m: {r["month"]: int(r["value"])
                      for _, r in grp[grp["metric"] == m].iterrows()}
                  for m in ("views", "edits")}
            for wid, grp in (timeseries.groupby("wals_id") if len(timeseries)
                             else [])
        },
    })
    log("  timeseries.json")

    write_json(os.path.join(PROCESSED, "features.json"), {
        "features": records(parameters),
        "codes": records(codes),
    })
    log("  features.json")

    write_json(os.path.join(PROCESSED, "feature_matrix.json"), {
        "language_keys": wide.index.tolist(),
        "feature_ids": feature_ids,
        "values": [[None if pd.isna(v) else str(v) for v in wide[fid].tolist()]
                   for fid in feature_ids],
    })
    log("  feature_matrix.json")

    # ------------------------------------------------------------------- report
    banner("8. 数据质量报告")
    name_of = dict(zip(dim_language["wals_id"], dim_language["name"]))
    lines = [
        "# 数据校验报告", "",
        "## 规模", "",
        f"- WALS values: {human(len(values))} 行",
        f"- WALS languages: {human(len(languages))} 行",
        f"- dim_language: {human(len(dim_language))} 行（主键 wals_id），"
        f"有经纬度 {human(has_coords)}",
        f"- 其中**真语言** {human(int(kinds['language']))} 行；"
        f"另 {human(len(dim_language) - int(kinds['language']))} 行是语系/语族/语支层级占位"
        f"（family {human(kinds.get('family', 0))}、genus {human(kinds.get('genus', 0))}、"
        f"subfamily {human(kinds.get('subfamily', 0))}），"
        f"导出给前端的 languages.json 已剔除",
        f"- fact_language_feature: {human(len(feat))} 行，"
        f"覆盖语言 {human(feat['wals_id'].nunique())}，"
        f"覆盖特征 {human(feat['feature_id'].nunique())}",
        f"- feature_vector: {human(wide.shape[0])} × {human(wide.shape[1])}，"
        f"填充率 {filled / total_cells * 100:.1f}%",
        f"- 时间序列: {human(len(timeseries))} 行",
        f"- 可关联 WALS 的维基版本: "
        f"{human(sum(1 for v in join.values() if v['joined']))}",
        "",
        "## 标识符模型（重要）", "",
        f"- WALS `ID` 唯一：{human(len(set(dim_language['wals_id'])))} 个 → **主键**",
        f"- `Glottocode` 不唯一：{human(int(dim_language['glottocode'].nunique()))} 个，"
        f"其中 {human(len(multi))} 个对应多个 WALS 变体",
        f"- 受影响变体记录：{human(int(multi.sum()))} 条",
        "",
        "WALS 的 Glottocode 指向「语言」层级，而 WALS 的分析单元是「变体」。",
        "例如 `swis1247` 同时是阿尔萨斯语与 5 种瑞士德语，特征取值互相冲突。",
        "以 Glottocode 作主键会静默合并这些变体并丢失数据，故改用 `wals_id`。",
        "",
        "变体最多的 Glottocode：", "",
    ]
    lines.append("| Glottocode | 变体数 | 成员 |")
    lines.append("|---|---|---|")
    for g, n in multi.head(8).items():
        members = dim_language[dim_language["glottocode"] == g]["name"].tolist()
        lines.append(f"| `{g}` | {n} | {'、'.join(m[:20] for m in members[:4])}"
                     f"{' …' if len(members) > 4 else ''} |")

    # the wiki join is inherently many-to-one: ISO 639-3 is language-level,
    # WALS is variety-level, so nearly every ISO code matches several rows
    amb = sum(1 for v in join.values() if v.get("join_ambiguous"))
    joined_n = sum(1 for v in join.values() if v["joined"])
    lines += [
        "",
        "## 维基关联的歧义（必须知道）", "",
        f"- 成功关联的维基版本：{human(joined_n)}",
        f"- 其中 ISO 码对应多个 WALS 条目的：**{human(amb)}**"
        f"（{amb / max(joined_n, 1) * 100:.0f}%）",
        "",
        "这不是数据错误，而是两个体系的粒度差异：**ISO 639-3 标识「语言」，",
        "WALS 收录的是「变体」**。例如维基的 `de` 对应 ISO `deu`，",
        "而 WALS 下 `stan1295` 有 6 条变体记录（标准德语、伯尔尼德语、苏黎世德语…）。",
        "",
        "处理方式：**按特征数据最丰富者择优**（并列时按 `wals_id` 取值，保证确定性），",
        "并在 `dim_wiki_edition.join_ambiguous` 与 `iso_candidates` 中显式记录，",
        "便于答辩时说明与复核。",
    ]

    lines += ["", "## 语系分布（Top 15）", ""]
    for fam, n in Counter(dim_language["family"]).most_common(15):
        lines.append(f"- {fam or '(空)'}: {human(n)}")

    lines += ["", "## 主要语区分布", ""]
    for ma, n in Counter(dim_language["macroarea"]).most_common():
        lines.append(f"- {ma or '(空)'}: {human(n)}")

    lines += ["", "## 特征覆盖率（决定条件对比交互能用哪些特征）", ""]
    cov = feat.groupby("feature_id")["wals_id"].nunique().sort_values(ascending=False)
    feat_name = dict(zip(parameters["ID"], parameters["Name"]))
    lines.append(f"- 特征总数: {human(len(cov))}")
    lines.append(f"- 每特征覆盖语言数：中位数 {int(cov.median())}，"
                 f"最少 {int(cov.min())}，最多 {int(cov.max())}")
    lines.append(f"- 覆盖 ≥ 300 个语言的特征: {human(int((cov >= 300).sum()))} 个")
    lines += ["", "| 覆盖最好的 8 个特征 | 语言数 |", "|---|---|"]
    for fid, n in cov.head(8).items():
        lines.append(f"| {feat_name.get(fid, fid)} | {human(int(n))} |")

    lines += ["", "## 活力增长最快 / 最慢（仅基线可靠的语言）", "",
              f"基线门槛：首 3 个月月均浏览量 ≥ {human(BASELINE_MIN)}。",
              "低于门槛的维基多为「早期未被统计、后来才开始记录」，",
              "其增长率是统计伪影而非真实增长，已排除。", ""]
    if reliable:
        ranked = sorted(reliable.items(), key=lambda kv: kv[1]["growth"])
        lines += ["| 语言 | 首 3 月均值 | 末 3 月均值 | 增长 |", "|---|---|---|---|"]
        for wid, s in ranked[:10] + ranked[-10:]:
            lines.append(f"| {name_of.get(wid, wid)} | {s['views_baseline']:,.0f} | "
                         f"{s['views_recent']:,.0f} | {s['growth'] * 100:+.1f}% |")

    artifacts = sorted(
        ((k, s) for k, s in vitality.items()
         if not s.get("baseline_ok") and s.get("growth") is not None),
        key=lambda kv: -kv[1]["growth"])[:8]
    lines += ["", "## 被排除的疑似统计伪影（示例）", "",
              "| 语言 | 首 3 月均值 | 末 3 月均值 | 表观增长 |", "|---|---|---|---|"]
    for wid, s in artifacts:
        lines.append(f"| {name_of.get(wid, wid)} | {s['views_baseline']:,.0f} | "
                     f"{s['views_recent']:,.0f} | {s['growth'] * 100:+,.0f}% |")

    with open(os.path.join(PROCESSED, "validation.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    log("  validation.md")

    banner("完成")
    log(f"  输出目录 -> {PROCESSED}")


if __name__ == "__main__":
    main()
