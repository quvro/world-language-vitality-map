# -*- coding: utf-8 -*-
"""Diagnose duplicate Glottocodes in WALS languages.csv."""
import csv
import os
import sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "data", "raw", "wals", "languages.csv")

with open(P, encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

print(f"总行数 = {len(rows):,}")
ids = [r["ID"] for r in rows]
gl = [r.get("Glottocode", "").strip() for r in rows]
print(f"unique ID          = {len(set(ids)):,}")
print(f"非空 Glottocode    = {sum(1 for g in gl if g):,}")
print(f"unique Glottocode  = {len({g for g in gl if g}):,}")

key = [g if g else i for g, i in zip(gl, ids)]
print(f"unique lang_key    = {len(set(key)):,}   <- 重复 {len(key) - len(set(key))}")

dupes = [g for g, n in Counter(key).items() if n > 1]
print(f"\n重复的 key 数 = {len(dupes)}")

by_key = defaultdict(list)
for r in rows:
    k = r["Glottocode"].strip() or r["ID"]
    by_key[k].append(r)

print("\n=== 重复示例（前 8 组）===")
for k in dupes[:8]:
    grp = by_key[k]
    print(f"\n  key = {k}   出现 {len(grp)} 次")
    for r in grp:
        print(f"    ID={r['ID']:<8} Name={r['Name'][:34]:<36} "
              f"Macroarea={r.get('Macroarea','')[:10]:<12} "
              f"ISO={r.get('ISO639P3code','')} Family={r.get('Family','')[:14]}")

# how many of the duplicates are genuinely distinct languages?
print("\n=== 重复 key 的名称是否相同 ===")
same_name = diff_name = 0
for k in dupes:
    names = {r["Name"] for r in by_key[k]}
    if len(names) == 1:
        same_name += 1
    else:
        diff_name += 1
print(f"  同名（可能是同一语言的多条记录）= {same_name}")
print(f"  不同名（可能是不同变体共用 Glottocode）= {diff_name}")

# does any duplicated key appear in the value table for both IDs?
print("\n=== 重复 key 在 fact 表中的取值是否冲突 ===")
with open(os.path.join(ROOT, "data", "raw", "wals", "values.csv"),
          encoding="utf-8") as fh:
    vals = list(csv.DictReader(fh))
by_lang = defaultdict(set)
for v in vals:
    by_lang[v["Language_ID"]].add((v["Parameter_ID"], v["Value"]))
conflict = 0
for k in dupes:
    ids_here = [r["ID"] for r in by_key[k]]
    if len(ids_here) < 2:
        continue
    base = by_lang.get(ids_here[0], set())
    for other in ids_here[1:]:
        if by_lang.get(other, set()) != base:
            conflict += 1
            break
print(f"  取值有冲突的重复组 = {conflict} / {len(dupes)}")
