"""列出 SQLite 全部表与行数，并看新加的 dim_endangerment 分布。"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = sqlite3.connect("data/processed/language_vitality.db")
tabs = [r[0] for r in c.execute(
    "select name from sqlite_master where type='table' order by name")]
total = 0
for t in tabs:
    n = c.execute('select count(*) from "%s"' % t).fetchone()[0]
    total += n
    print(f"  {t:<28} {n:>8,}")
print(f"  {'合计':<28} {total:>8,}")
print()
print("  dim_endangerment:")
for src, lv, n in c.execute(
        "select source, level, count(*) from dim_endangerment "
        "group by source, level order by source, level"):
    print(f"    {src:<8} level={lv}  {n:>5,}")
print()
print("  抽查：康沃尔语 / 马恩岛语（口语已灭绝但维基在增长）")
for gc in ("corn1251", "manx1241", "stan1295"):
    r = c.execute("select glottocode, level, source, label_zh from dim_endangerment "
                  "where glottocode=?", (gc,)).fetchone()
    print(f"    {gc:<10} {r}")
