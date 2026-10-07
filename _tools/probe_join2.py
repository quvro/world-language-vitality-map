# -*- coding: utf-8 -*-
"""Resolve the real WALS x Wikipedia join size by mapping ISO 639-1 -> ISO 639-3."""
import base64
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
OUT_FILE = os.path.join(OUT, "join_probe2.txt")
UA = "CourseProjectProbe/1.0 (student research; contact: none)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:210], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url, timeout=120, as_json=True, accept="*/*"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw


# --- ISO 639-1 <-> 639-3 from Wikidata (ONE query) -------------------------
log("=" * 78)
log("### 1. 从 Wikidata 取 ISO 639-1 <-> 639-3 映射（单次查询）")
iso1_to_3: dict[str, str] = {}
iso3_to_1: dict[str, str] = {}
q = """
SELECT ?iso1 ?iso3 WHERE {
  ?item wdt:P218 ?iso1 ; wdt:P220 ?iso3 .
}
"""
url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
    {"query": q, "format": "json"})
for attempt in range(4):
    try:
        d = get(url, accept="application/sparql-results+json")
        for row in d["results"]["bindings"]:
            a = row["iso1"]["value"].lower()
            b = row["iso3"]["value"].lower()
            iso1_to_3[a] = b
            iso3_to_1[b] = a
        break
    except Exception as e:  # noqa: BLE001
        log(f"  attempt {attempt + 1}: {type(e).__name__} {str(e)[:80]}")
        time.sleep(80)
log(f"  拿到 {len(iso1_to_3)} 组 639-1 -> 639-3 映射")

# --- Wikipedia editions ----------------------------------------------------
sm = get("https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json")
editions: dict[str, str] = {}
for k, v in sm["sitematrix"].items():
    if not k.isdigit():
        continue
    code = (v.get("code") or "").lower()
    for site in v.get("site", []):
        if site.get("code") == "wiki" and site.get("url"):
            editions[code] = v.get("name")
log("")
log(f"### 2. 维基百科语言版本 = {len(editions)}")

# --- WALS ------------------------------------------------------------------
listing = get("https://api.github.com/repos/cldf-datasets/wals/contents/cldf")
by_name = {f["name"]: f for f in listing}
blob = get(by_name["languages.csv"]["git_url"])
wals = list(csv.DictReader(io.StringIO(
    base64.b64decode(blob["content"]).decode("utf-8", "replace"))))

wals_by_code: dict[str, dict] = {}
for r in wals:
    keys = []
    if r.get("ISO639P3code"):
        keys.append(r["ISO639P3code"].strip().lower())
    for tok in (r.get("ISO_codes") or "").replace(";", " ").replace(",", " ").split():
        keys.append(tok.strip().lower())
    for k in keys:
        if k:
            wals_by_code.setdefault(k, r)
log(f"### 3. WALS 语言 = {len(wals)}，可索引代码 = {len(wals_by_code)}")

# --- join, now with the 639-1 -> 639-3 hop --------------------------------
log("")
log("### 4. JOIN（两级）")
direct, via_iso1, unmatched = [], [], []
for code in sorted(editions):
    if code in wals_by_code:
        direct.append(code)
    elif code in iso1_to_3 and iso1_to_3[code] in wals_by_code:
        via_iso1.append(code)
    else:
        unmatched.append(code)

total = len(direct) + len(via_iso1)
log(f"  直接命中(三位码)         = {len(direct)}")
log(f"  经 639-1 -> 639-3 命中的 = {len(via_iso1)}")
log(f"  **合计可连接语言         = {total}**")
log(f"  仍连不上的               = {len(unmatched)}")
log(f"  连不上的样例 = {unmatched[:35]}")

# --- time-series size ------------------------------------------------------
log("")
log("### 5. 组合后的数据规模")
months = 127  # 2015-07 .. 2026-01 monthly
log(f"  可连接语言 {total} x 时间点 {months} = {total * months:,} 条时间序列记录")
log(f"  WALS 结构数据                     = 76,475 条")
log(f"  合计                              = {total * months + 76475:,} 条")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
