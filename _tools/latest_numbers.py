"""产出 README 需要引用的最新数字（增长榜、规模表）。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = "data/processed"
L = json.load(open(os.path.join(D, "languages.json"), encoding="utf-8"))
T = json.load(open(os.path.join(D, "timeseries.json"), encoding="utf-8"))
Z = json.load(open(os.path.join(D, "zh_labels.json"), encoding="utf-8"))


def cn(l):
    return (Z["by_iso639p3"].get((l.get("iso639p3") or "").lower())
            or Z["by_glottocode"].get(l.get("glottocode") or "")
            or l["name"])


r = [l for l in L if l.get("baseline_ok") and l.get("growth") is not None]
r.sort(key=lambda x: x["growth"])
print("最跌 5:")
for l in r[:5]:
    print(f"  {cn(l)[:14]:<16} {l['name'][:22]:<24} {l['growth'] * 100:+.1f}%")
print("最涨 5:")
for l in r[-5:]:
    print(f"  {cn(l)[:14]:<16} {l['name'][:22]:<24} {l['growth'] * 100:+,.0f}%")
print()
mo = sorted({m for s in T["by_language"].values() for m in s["views"]})
print(f"月份 {mo[0]}..{mo[-1]} ({len(mo)})")
print(f"语言 {len(L)}, 有坐标 {sum(1 for l in L if l.get('latitude') and l.get('longitude'))}")
print(f"有维基 {sum(1 for l in L if l.get('wiki_code'))}, 有增长率 {len(r)}, 基线可靠 {sum(1 for l in L if l.get('baseline_ok'))}")
