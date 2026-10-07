# -*- coding: utf-8 -*-
"""Find a comparison / time dimension to bolt onto WALS.

Candidate 1: Wikimedia per-language-edition time series (digital vitality)
Candidate 2: D-PLACE cross-cultural database (cultural trait comparison)
Candidate 3: Glottolog endangerment status (vitality, static)
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
OUT_FILE = os.path.join(OUT, "dimension_probe.txt")
UA = "CourseProjectProbe/1.0 (student research; contact: none)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:210], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url, timeout=90, as_json=True, ua=UA):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
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
            body = e.read()[:200].decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            pass
        log(f"  HTTP {e.code} {e.reason}  {body}")
    except Exception as e:  # noqa: BLE001
        log(f"  FAILED: {type(e).__name__}: {str(e)[:140]}")


# ------------------------------------------- 1. Wikimedia site matrix (language editions)
def site_matrix():
    d = get("https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json")
    sm = d.get("sitematrix", {})
    editions = []
    for k, v in sm.items():
        if not k.isdigit():
            continue
        code = v.get("code")
        for site in v.get("site", []):
            if site.get("code") == "wiki":
                editions.append({
                    "lang": code,
                    "name": v.get("name"),
                    "url": site.get("url"),
                    "articles": site.get("articles"),
                    "active": site.get("active"),
                })
    log(f"  维基百科语言版本总数 = {len(editions)}")
    eds = [e for e in editions if e["url"]]
    log(f"  有 url 的 = {len(eds)}")
    top = sorted(eds, key=lambda e: -(e["articles"] or 0))[:8]
    for e in top:
        log(f"    {e['lang']:<8} {str(e['name'])[:18]:<20} articles={e['articles']}")
    small = [e for e in eds if (e["articles"] or 0) < 1000]
    log(f"  条目 < 1000 的版本数 = {len(small)}  (数字化濒危的语言)")


# ------------------------------------------- 2. Wikimedia pageviews time series
def pageviews():
    base = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/"
            "{proj}/all-access/user/monthly/{start}/{end}")
    for proj in ["de.wikipedia.org", "ja.wikipedia.org", "sw.wikipedia.org"]:
        url = base.format(proj=proj, start="2016010100", end="2026010100")
        d = get(url)
        items = d.get("items") or []
        log(f"  {proj:<20} 月数 = {len(items)}")
        if items:
            first, last = items[0], items[-1]
            log(f"      {first['timestamp']}: {first['views']:,} views")
            log(f"      {last['timestamp']}: {last['views']:,} views")
            log(f"      字段 = {sorted(first.keys())}")


# ------------------------------------------- 3. D-PLACE cross-cultural data
def dplace():
    for repo in ["D-PLACE/dplace-data", "D-PLACE/dplace"]:
        try:
            d = get(f"https://api.github.com/repos/{repo}/contents/")
            log(f"  {repo} 顶层:")
            for f in d[:24]:
                log(f"    {f['type']:<5} {f['name']:<40} {f.get('size', 0):>10} B")
            return
        except urllib.error.HTTPError as e:
            log(f"  {repo}: HTTP {e.code}")


def dplace_datasets():
    d = get("https://api.github.com/repos/D-PLACE/dplace-data/contents/datasets")
    log(f"  datasets 目录条目数 = {len(d)}")
    for f in d[:30]:
        log(f"    {f['name']}")


# ------------------------------------------- 4. Glottolog endangerment (AES)
def glottolog_aes():
    # Glottolog CLDF via GitHub blob API (raw is blocked on this host)
    meta = get("https://api.github.com/repos/glottolog/glottolog-cldf/contents/cldf")
    names = [f["name"] for f in meta]
    log(f"  glottolog-cldf/cldf 文件: {names}")
    want = [f for f in meta if f["name"] == "ValueTable.csv"]
    if want:
        log(f"  ValueTable.csv 大小 = {want[0]['size']} B")


# ------------------------------------------- 5. CLDF catalog (more time-depth data)
def cldf_catalog():
    d = get("https://api.github.com/repos/cldf/cldf/contents/")
    log(f"  cldf/cldf 顶层: {[f['name'] for f in d][:20]}")


probe("1. 维基百科语言版本清单（语言 × 数字规模）", site_matrix)
probe("2. 维基百科逐语言版本月度浏览时间序列（时间维度）", pageviews)
probe("3. D-PLACE 跨文化数据库（文化比较维度）", dplace)
probe("4. D-PLACE datasets 目录", dplace_datasets)
probe("5. Glottolog CLDF 濒危状态表", glottolog_aes)
probe("6. CLDF 目录（含时间深度的语系树数据集）", cldf_catalog)

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
