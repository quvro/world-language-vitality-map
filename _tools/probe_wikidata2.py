# -*- coding: utf-8 -*-
"""Second Wikidata probe: 3 critical queries, spaced out (WDQS is rate-limiting 1/min)."""
import json
import os
import time
import urllib.parse
import urllib.request

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "CourseProjectFeasibilityProbe/1.0 (student research)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
OUT_FILE = os.path.join(OUT, "wikidata_probe2.txt")
SLEEP = 70

lines: list[str] = []


def log(text: str = "") -> None:
    lines.append(text)
    print(text, flush=True)


def sparql(name: str, query: str, attempts: int = 4) -> None:
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    log("=" * 72)
    log(f"### {name}")
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.load(resp)
            rows = data["results"]["bindings"]
            log(f"  rows: {len(rows)}")
            for row in rows:
                parts = [row[v]["value"] for v in data["head"]["vars"] if v in row]
                log("  - " + " | ".join(parts))
            return
        except Exception as exc:  # noqa: BLE001
            log(f"  attempt {attempt} failed: {exc}")
            if attempt < attempts:
                time.sleep(SLEEP)
    log("  GAVE UP")


sparql("神祇关系属性密度（决定家族/师承网络图可行性）", """
SELECT
  (COUNT(?d) AS ?total)
  (COUNT(?father) AS ?hasFather)
  (COUNT(?mother) AS ?hasMother)
  (COUNT(?spouse) AS ?hasSpouse)
  (COUNT(?child) AS ?hasChild)
  (COUNT(?sibling) AS ?hasSibling)
WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 .
  OPTIONAL { ?d wdt:P22 ?father }
  OPTIONAL { ?d wdt:P25 ?mother }
  OPTIONAL { ?d wdt:P26 ?spouse }
  OPTIONAL { ?d wdt:P40 ?child }
  OPTIONAL { ?d wdt:P3373 ?sibling }
}
""")
time.sleep(SLEEP)

sparql("中国神话(Q210677)相关神祇数量与样本", """
SELECT ?d ?dLabel ?dDescription WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 .
  ?d wdt:P361 wd:Q210677 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 25
""")
time.sleep(SLEEP)

sparql("希腊神话家族关系样本", """
SELECT ?dLabel ?fatherLabel ?motherLabel ?spouseLabel ?childLabel WHERE {
  ?d wdt:P31/wdt:P279* wd:Q178885 ; wdt:P361 wd:Q34726 .
  OPTIONAL { ?d wdt:P22 ?father }
  OPTIONAL { ?d wdt:P25 ?mother }
  OPTIONAL { ?d wdt:P26 ?spouse }
  OPTIONAL { ?d wdt:P40 ?child }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "zh,en". }
} LIMIT 25
""")

os.makedirs(OUT, exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print(f"\nwrote {OUT_FILE}")
