# -*- coding: utf-8 -*-
"""Quick integrity check of the built database and exported JSON."""
import json
import os
import sqlite3
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "processed", "language_vitality.db")

con = sqlite3.connect(DB)
print("=== SQLite 表行数 ===")
tables = [r[0] for r in con.execute(
    "select name from sqlite_master where type='table' order by name")]
for t in tables:
    n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
    print(f"  {t:<28} {n:>8,}")

print("\n=== 关键完整性检查 ===")
checks = [
    ("wals_id 主键唯一", 'select count(*)=count(distinct wals_id) from dim_language'),
    ("glottocode 唯一?", 'select count(*)=count(distinct glottocode) from dim_language'),
    ("有经纬度的语言", 'select count(*) from dim_language where latitude is not null '
                 'and longitude is not null'),
    ("可关联维基的语言", 'select count(*) from dim_wiki_edition where joined=1'),
    ("关联有歧义的版本", 'select count(*) from dim_wiki_edition where join_ambiguous=1'),
    ("月份键非法行数", "select count(*) from fact_language_timeseries "
                "where month not glob '[0-9][0-9][0-9][0-9][0-9][0-9]'"),
    ("时间序列语言数", 'select count(distinct wals_id) from fact_language_timeseries'),
    ("特征数", 'select count(*) from dim_feature'),
    ("特征取值定义数", 'select count(*) from dim_code'),
    ("feature_vector 列数", None),
]
for label, sql in checks:
    if sql is None:
        cols = [r[1] for r in con.execute("pragma table_info(feature_vector)")]
        print(f"  {label:<22}: {len(cols) - 1} 个特征列 + 1 个主键")
        continue
    val = con.execute(sql).fetchone()[0]
    note = ""
    if "非法" in label and val:
        note = "  <-- 应为 0"
    if label == "glottocode 唯一?" and not val:
        note = "  (预期为 False：一个 Glottocode 可覆盖多个变体)"
    print(f"  {label:<22}: {val}{note}")

print("\n=== 多变体 Glottocode Top 5 ===")
for g, n in con.execute(
        "select glottocode, count(*) c from dim_language "
        "where glottocode is not null group by glottocode "
        "having c > 1 order by c desc limit 5"):
    print(f"  {g:<12} {n} 个变体")

print("\n=== 语系 Top 10 ===")
for fam, n in con.execute(
        "select family, count(*) c from dim_language "
        "group by family order by c desc limit 10"):
    print(f"  {fam or '(空)':<18} {n:>5,}")

con.close()

print("\n=== 前端 JSON ===")
for name in ("languages.json", "timeseries.json", "features.json",
             "feature_matrix.json"):
    p = os.path.join(ROOT, "data", "processed", name)
    obj = json.load(open(p, encoding="utf-8"))
    if name == "languages.json":
        joined = sum(1 for r in obj if r.get("wiki_code"))
        withgrowth = sum(1 for r in obj if r.get("growth") is not None)
        print(f"  {name:<22} {len(obj):>6,} 条  (有维基 {joined}, 有增长率 {withgrowth})")
    elif name == "feature_matrix.json":
        print(f"  {name:<22} {len(obj['language_keys']):>6,} 语言 x "
              f"{len(obj['feature_ids'])} 特征")
    elif name == "timeseries.json":
        print(f"  {name:<22} {len(obj['by_language']):>6,} 个语言有序列")
    else:
        print(f"  {name:<22} {len(obj['features'])} 特征, {len(obj['codes'])} 取值")
