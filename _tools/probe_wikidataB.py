# -*- coding: utf-8 -*-
"""Probe B v2: cross-cultural *domain* (职能) data for deities — the decisive tests.

Fixes the GBK stdout crash from v1 and adds a common-sense sanity check:
do the thunder/sun/war gods it returns actually match what a human would expect?
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
OUT_FILE = os.path.join(OUT, "wikidata_probeB.txt")
SLEEP = 78

lines: list[str] = []


def log(text: str = "") -> None:
    lines.append(text)
    try:
        print(text[:220], flush=True)
    except Exception:  # noqa: BLE001
        pass


def sparql(name: str, query: str, attempts: int = 6) -> None:
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
            log(f"  attempt {attempt}: {type(exc).__name__}: {str(exc)[:90]}")
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


# Q1: the full landscape of "domain" classes under deity
sparql("职能类目全貌（deity 的子类，成员 >= 20）", """
SELECT ?class ?classLabel (COUNT(?d) AS ?c) WHERE {
  ?class wdt:P279* wd:Q178885 .
  ?d wdt:P31 ?class .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} GROUP BY ?class ?classLabel HAVING (COUNT(?d) >= 20) ORDER BY DESC(?c) LIMIT 45
""")
time.sleep(SLEEP)

# Q2: domain x mythology matrix
sparql("职能 × 神话体系 矩阵", """
SELECT ?classLabel ?mythLabel (COUNT(?d) AS ?c) WHERE {
  ?d wdt:P31 ?class ; wdt:P361 ?myth .
  ?class wdt:P279* wd:Q178885 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} GROUP BY ?classLabel ?mythLabel ORDER BY DESC(?c) LIMIT 45
""")
time.sleep(SLEEP)

# Q3: common-sense check — who is actually in the top domain classes?
sparql("常识校验：主要职能类目的具体成员与所属神话", """
SELECT ?classLabel ?dLabel ?mythLabel WHERE {
  VALUES ?class { wd:Q1916821 wd:Q41863069 wd:Q2803758 wd:Q842697 }
  ?d wdt:P31 ?class .
  OPTIONAL { ?d wdt:P361 ?myth }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 60
""")
time.sleep(SLEEP)

# Q4: cross-cultural equivalence (the "流变" relation)
sparql("等同神 P460：覆盖量与样本（文化流变的直接证据）", """
SELECT ?dLabel ?oLabel WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 ; wdt:P460 ?o .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 40
""")
time.sleep(SLEEP)

sparql("等同神 P460 总量", """
SELECT (COUNT(DISTINCT ?d) AS ?deities) WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 ; wdt:P460 ?o .
}
""")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
