# -*- coding: utf-8 -*-
"""Probe candidate datasets: economy/culture, >=10k rows, easy joins, niche.

Tests real endpoints and reports hard numbers. Writes UTF-8 to _refs_out/candidates.txt
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
os.makedirs(OUT, exist_ok=True)
OUT_FILE = os.path.join(OUT, "candidates.txt")
UA = "Mozilla/5.0 (compatible; CourseProjectProbe/1.0)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:200], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url: str, timeout: int = 45, as_json: bool = True):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw


def probe(name: str, fn) -> None:
    log("=" * 78)
    log(f"### {name}")
    try:
        fn()
    except urllib.error.HTTPError as e:
        log(f"  HTTP {e.code} {e.reason}")
    except Exception as e:  # noqa: BLE001
        log(f"  FAILED: {type(e).__name__}: {str(e)[:150]}")


# ---------------------------------------------------------------- 1. Met Museum
def met():
    d = get("https://collectionapi.metmuseum.org/public/collection/v1/objects")
    log(f"  全部藏品对象数 total = {d.get('total')}")
    log(f"  objectIDs 返回长度 = {len(d.get('objectIDs') or [])}")
    for q in ["china", "japan", "egypt", "greek", "islamic"]:
        s = get("https://collectionapi.metmuseum.org/public/collection/v1/search"
                f"?q={urllib.parse.quote(q)}&hasImages=true")
        log(f"  search q={q:<8} total = {s.get('total')}")
    # detail record fields
    oid = (d.get("objectIDs") or [1])[0]
    o = get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}")
    log(f"  详情样例 id={oid} 字段({len(o)}个): {sorted(o.keys())}")


# ------------------------------------------------- 2. Art Institute of Chicago
def aic():
    d = get("https://api.artic.edu/api/v1/artworks?limit=1&page=1")
    log(f"  pagination.total = {d['pagination']['total']}")
    log(f"  记录字段({len(d['data'][0])}个): {sorted(d['data'][0].keys())}")
    r = d["data"][0]
    for k in ("id", "title", "date_display", "place_of_origin", "medium_display",
              "department_title", "artist_display"):
        if k in r:
            log(f"    {k}: {str(r[k])[:80]}")


# ----------------------------------------------------------- 3. Glottolog / WALS
def glottolog():
    d = get("https://glottolog.org/resourcemap.json?rsc=language")
    feats = d.get("features") or []
    log(f"  Glottolog language 点位数 = {len(feats)}")
    if feats:
        log(f"  单条属性: {json.dumps(feats[0].get('properties'), ensure_ascii=False)[:200]}")


def wals_repo():
    d = get("https://api.github.com/repos/cldf-datasets/wals/contents/cldf")
    log("  WALS CLDF 目录内容:")
    for f in d:
        log(f"    {f['name']:<34} {f.get('size', 0):>10} B")


# ------------------------------------------- 4. Allen-Unger commodity prices
def gcpdb():
    raw = get("https://www.gcpdb.info/", as_json=False)
    log(f"  首页字节数 = {len(raw)}")
    txt = raw.decode("utf-8", "replace")
    for kw in ("download", "csv", "xlsx", "data"):
        log(f"    含 '{kw}': {txt.lower().count(kw)} 次")


# ------------------------------------------- 5. TMDB / Open Library sanity
def openlibrary():
    d = get("https://openlibrary.org/search.json?q=the+lord+of+the+rings&limit=1")
    log(f"  Open Library 查询命中 numFound = {d.get('numFound')}")
    log(f"  单条字段: {sorted((d.get('docs') or [{}])[0].keys())[:22]}")


probe("1. 大都会艺术博物馆 Met Open Access API（文化·文物）", met)
probe("2. 芝加哥艺术博物馆 AIC API（文化·文物）", aic)
probe("3. Glottolog 语言谱系（文化·语言学）", glottolog)
probe("4. WALS 世界语言结构（文化·语言学，CLDF/CSV）", wals_repo)
probe("5. Allen-Unger 全球历史商品价格库（经济史）", gcpdb)
probe("6. Open Library 书目（文化·出版）", openlibrary)

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
