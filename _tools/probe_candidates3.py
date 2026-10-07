# -*- coding: utf-8 -*-
"""Candidate probe round 3: more no-key museum APIs + a raw.githubusercontent workaround."""
import csv
import io
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
OUT_FILE = os.path.join(OUT, "candidates3.txt")
UA = "Mozilla/5.0 (compatible; CourseProjectProbe/1.0)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:210], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url, timeout=60, as_json=True, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw


def probe(name, fn):
    log("=" * 78)
    log(f"### {name}")
    try:
        fn()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read()[:180].decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        log(f"  HTTP {e.code} {e.reason}  {body}")
    except Exception as e:  # noqa: BLE001
        log(f"  FAILED: {type(e).__name__}: {str(e)[:130]}")


# ------------------------------------------------ V&A Museum (no key?)
def vam():
    d = get("https://api.vam.ac.uk/v2/objects/search?page_size=1&q=dress")
    log(f"  info: {json.dumps(d.get('info'), ensure_ascii=False)[:200]}")
    recs = d.get("records") or []
    if recs:
        log(f"  记录字段({len(recs[0])}): {sorted(recs[0].keys())}")
        r = recs[0]
        for k in ("systemNumber", "objectType", "title", "placeOfOrigin",
                  "date", "materialsAndTechniques", "productionDates"):
            log(f"    {k}: {str(r.get(k))[:80]}")


# ------------------------------------------------ Cleveland Museum of Art
def cma():
    d = get("https://openaccess-api.clevelandart.org/api/artworks/?limit=1")
    log(f"  info: {json.dumps(d.get('info'), ensure_ascii=False)[:200]}")
    recs = d.get("data") or []
    if recs:
        log(f"  记录字段({len(recs[0])}): {sorted(recs[0].keys())[:45]}")
        r = recs[0]
        for k in ("id", "title", "creation_date", "culture", "department",
                  "type", "technique", "share_license_status"):
            log(f"    {k}: {str(r.get(k))[:80]}")


# ------------------------------------------------ AIC deep check
def aic2():
    d = get("https://api.artic.edu/api/v1/artworks?limit=1&page=1"
            "&fields=id,title,date_display,date_start,date_end,place_of_origin,"
            "medium_display,department_title,classification_title,artist_title,"
            "style_title,color,is_public_domain")
    log(f"  可用 fields 过滤: OK")
    log(f"  total = {d['pagination']['total']}")
    log(f"  样例: {json.dumps(d['data'][0], ensure_ascii=False)[:420]}")
    # facets / aggregations support
    try:
        f = get("https://api.artic.edu/api/v1/artworks/search?q=&size=0"
                "&facets=department_title,place_of_origin,medium_display")
        aggs = f.get("aggregations") or {}
        log(f"  聚合(facets)支持: {list(aggs.keys())}")
        for k, v in list(aggs.items())[:2]:
            buckets = (v.get("buckets") or [])[:5]
            log(f"    {k}: {[(b['key'], b['doc_count']) for b in buckets]}")
    except Exception as e:  # noqa: BLE001
        log(f"  facets 失败: {str(e)[:90]}")


# ------------------------------------------------ jsDelivr for GitHub raw
def jsdelivr_wals():
    base = "https://cdn.jsdelivr.net/gh/cldf-datasets/wals@main/cldf/"
    for name in ["values.csv", "languages.csv", "parameters.csv", "codes.csv"]:
        try:
            raw = get(base + name, as_json=False)
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8", "replace"))))
            log(f"  {name:<16} {len(raw):>9} B  行数={len(rows) - 1}")
            log(f"     表头: {rows[0][:16]}")
        except Exception as e:  # noqa: BLE001
            log(f"  {name}: {type(e).__name__} {str(e)[:70]}")


def jsdelivr_glottolog():
    url = ("https://cdn.jsdelivr.net/gh/glottolog/glottolog-cldf@main/"
           "cldf/ValueTable.csv")
    try:
        raw = get(url, as_json=False, timeout=90)
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8", "replace"))))
        log(f"  Glottolog CLDF ValueTable: {len(raw)} B, 行数={len(rows) - 1}")
    except Exception as e:  # noqa: BLE001
        log(f"  ValueTable: {type(e).__name__} {str(e)[:80]}")
    for name in ["LanguageTable.csv", "languages.csv"]:
        try:
            raw = get(("https://cdn.jsdelivr.net/gh/glottolog/glottolog-cldf@main/"
                       f"cldf/{name}"), as_json=False, timeout=90)
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8", "replace"))))
            log(f"  {name}: {len(raw)} B, 行数={len(rows) - 1}")
            log(f"     表头: {rows[0][:14]}")
        except Exception as e:  # noqa: BLE001
            log(f"  {name}: {type(e).__name__} {str(e)[:70]}")


probe("1. V&A 博物馆 API（是否免 key）", vam)
probe("2. 克利夫兰艺术博物馆 API（是否免 key）", cma)
probe("3. 芝加哥艺术学院 AIC 深度检查（字段过滤 / 聚合）", aic2)
probe("4. jsDelivr 代理 GitHub raw（解决 raw 被墙）", jsdelivr_wals)
probe("5. Glottolog CLDF（语言谱系，经 jsDelivr）", jsdelivr_glottolog)

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
