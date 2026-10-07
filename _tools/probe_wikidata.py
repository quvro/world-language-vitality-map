# -*- coding: utf-8 -*-
"""Probe Wikidata for mythology/deity coverage — evidence for topic feasibility.

Writes UTF-8 results to _refs_out/wikidata_probe.txt (console is GBK on this host).
"""
import json
import os
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
SEARCH = "https://www.wikidata.org/w/api.php"
UA = "CourseProjectFeasibilityProbe/1.0 (student research)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
os.makedirs(OUT, exist_ok=True)
OUT_FILE = os.path.join(OUT, "wikidata_probe.txt")

lines: list[str] = []


def log(text: str = "") -> None:
    lines.append(text)


def sparql(name: str, query: str) -> list[dict]:
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    log("=" * 72)
    log(f"### {name}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
    except Exception as exc:  # noqa: BLE001
        log(f"  FAILED: {exc}")
        return []
    rows = data["results"]["bindings"]
    log(f"  rows: {len(rows)}")
    for row in rows:
        parts = [row[v]["value"] for v in data["head"]["vars"] if v in row]
        log("  - " + " | ".join(parts))
    return rows


def wb_search(term: str, lang: str = "zh") -> None:
    url = SEARCH + "?" + urllib.parse.urlencode(
        {"action": "wbsearchentities", "search": term, "language": lang,
         "uselang": lang, "format": "json", "limit": 5}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    log("=" * 72)
    log(f"### 实体搜索: {term} ({lang})")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except Exception as exc:  # noqa: BLE001
        log(f"  FAILED: {exc}")
        return
    for hit in data.get("search", []):
        log(f"  - {hit['id']} | {hit.get('label','')} | {hit.get('description','')}")


# --- 0. locate the mythology entities we care about -------------------------
for term in ["中国神话", "希腊神话", "北欧神话", "埃及神话", "日本神话"]:
    wb_search(term)

# --- 1. overall deity count ------------------------------------------------
sparql("神祇实体总数", """
SELECT (COUNT(?d) AS ?c) WHERE { ?d wdt:P31/wdt:P279* wd:Q178885 . }
""")

# --- 2. how dense are the genealogical relations? --------------------------
sparql("神祇关系属性密度（决定网络图可行性）", """
SELECT
  (COUNT(?d) AS ?total)
  (COUNT(?father) AS ?hasFather)
  (COUNT(?mother) AS ?hasMother)
  (COUNT(?spouse) AS ?hasSpouse)
  (COUNT(?child) AS ?hasChild)
WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 .
  OPTIONAL { ?d wdt:P22 ?father }
  OPTIONAL { ?d wdt:P25 ?mother }
  OPTIONAL { ?d wdt:P26 ?spouse }
  OPTIONAL { ?d wdt:P40 ?child }
}
""")

# --- 3. mythology groups (P361) -------------------------------------------
sparql("神祇按神话体系分组 Top20", """
SELECT ?mythLabel (COUNT(?d) AS ?c) WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 .
  ?d wdt:P361 ?myth .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} GROUP BY ?mythLabel ORDER BY DESC(?c) LIMIT 20
""")

# --- 4. Greek genealogy sample --------------------------------------------
sparql("希腊神话家族关系样本", """
SELECT ?dLabel ?fatherLabel ?motherLabel ?spouseLabel ?childLabel WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 ; wdt:P361 wd:Q34726 .
  OPTIONAL { ?d wdt:P22 ?father }
  OPTIONAL { ?d wdt:P25 ?mother }
  OPTIONAL { ?d wdt:P26 ?spouse }
  OPTIONAL { ?d wdt:P40 ?child }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 20
""")

# --- 5. Chinese mythology coverage ----------------------------------------
sparql("中国神话相关神祇样本", """
SELECT ?d ?dLabel ?dDescription WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 .
  ?d wdt:P361 wd:Q1065809 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 20
""")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print(f"wrote {OUT_FILE} ({len(lines)} lines)")
