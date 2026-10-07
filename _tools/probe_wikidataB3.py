# -*- coding: utf-8 -*-
"""Probe B v3 — the DECISIVE test.

v2 revealed that joining function-class to culture-class via P361 (part of mythology)
is too sparse (only ~8-9 members per cell). But a deity item usually carries MULTIPLE
P31 (instance of) statements: e.g. Zeus is P31 both 雷神 and 希腊神.

So the correct join for a "职能 x 文明" matrix is P31 INTERSECT P31, not P361.

This query settles whether project B's core interaction is buildable.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "CourseProjectFeasibilityProbe/1.0 (student research)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
os.makedirs(OUT, exist_ok=True)
OUT_FILE = os.path.join(OUT, "wikidata_probeB_matrix.txt")
SLEEP = 95

# 职能 (function/domain)
FUNCS = {
    "Q1916821": "水神", "Q41863069": "戰神", "Q2803758": "冥神", "Q842697": "雷神",
    "Q511056": "太阳神", "Q1569856": "月神", "Q60994492": "天神",
    "Q60995523": "國神", "Q3027575": "河神", "Q1470705": "生育之神",
    "Q635155": "創造神", "Q205985": "女神",
}
# 文明 (culture / pantheon)
CULTS = {
    "Q22989102": "希腊", "Q11688446": "罗马", "Q146083": "埃及",
    "Q16513881": "北欧", "Q465434": "凯尔特", "Q979507": "印度教",
    "Q3027597": "道教", "Q32066628": "阿兹特克", "Q42594143": "玛雅",
    "Q61961377": "美索不达米亚", "Q4436935": "斯拉夫", "Q42593818": "伊特鲁里亚",
}

lines: list[str] = []


def log(text: str = "") -> None:
    lines.append(text)
    try:
        print(text[:230], flush=True)
    except Exception:  # noqa: BLE001
        pass


def sparql(name: str, query: str, attempts: int = 5) -> None:
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    log("=" * 78)
    log(f"### {name}")
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.load(resp)
        except Exception as exc:  # noqa: BLE001
            log(f"  attempt {attempt}: {type(exc).__name__}: {str(exc)[:80]}")
            if attempt < attempts:
                time.sleep(SLEEP)
            continue
        rows = data["results"]["bindings"]
        log(f"  rows: {len(rows)}")
        for row in rows:
            parts = [row[v]["value"] for v in data["head"]["vars"] if v in row]
            log("  - " + " | ".join(parts))
        return
    log("  GAVE UP")


func_vals = " ".join(f"wd:{q}" for q in FUNCS)
cult_vals = " ".join(f"wd:{q}" for q in CULTS)

# Q1: the matrix itself
sparql(f"职能 × 文明 矩阵（P31 交集法）  职能{len(FUNCS)}种 x 文明{len(CULTS)}种", f"""
SELECT ?funcLabel ?cultLabel (COUNT(DISTINCT ?d) AS ?c) WHERE {{
  VALUES ?func {{ {func_vals} }}
  VALUES ?cult {{ {cult_vals} }}
  ?d wdt:P31 ?func ; wdt:P31 ?cult .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}} GROUP BY ?funcLabel ?cultLabel ORDER BY DESC(?c) LIMIT 60
""")
time.sleep(SLEEP)

# Q2: sanity check — print the actual names so we can eyeball correctness
sparql("常识校验：雷神/太阳神/冥神/水神 在各文明中的具体成员", f"""
SELECT ?funcLabel ?cultLabel ?dLabel WHERE {{
  VALUES ?func {{ wd:Q842697 wd:Q511056 wd:Q2803758 wd:Q1916821 wd:Q41863069 }}
  VALUES ?cult {{ wd:Q22989102 wd:Q11688446 wd:Q146083 wd:Q16513881 wd:Q979507 wd:Q3027597 }}
  ?d wdt:P31 ?func ; wdt:P31 ?cult .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}} LIMIT 90
""")
time.sleep(SLEEP)

# Q3: how many deities carry >= 1 function class at all (coverage)
sparql("覆盖度：带职能类目的神祇总数 vs 神祇总数", f"""
SELECT
  (COUNT(DISTINCT ?d) AS ?withFunction)
WHERE {{
  VALUES ?func {{ {func_vals} }}
  ?d wdt:P31 ?func .
}}
""")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
