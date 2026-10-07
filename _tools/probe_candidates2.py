# -*- coding: utf-8 -*-
"""Candidate probe round 2: fix the failures and test economy-side options."""
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
OUT_FILE = os.path.join(OUT, "candidates2.txt")
UA = "Mozilla/5.0 (compatible; CourseProjectProbe/1.0)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:210], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url: str, timeout: int = 60, as_json: bool = True, headers: dict | None = None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw


def probe(name: str, fn) -> None:
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
        log(f"  FAILED: {type(e).__name__}: {str(e)[:130]}")


# ------------------------------------------------------ Met search, take 2
def met_search():
    for url in [
        "https://collectionapi.metmuseum.org/public/collection/v1/search?q=china",
        "https://collectionapi.metmuseum.org/public/collection/v1/search?departmentId=6&q=*",
        "https://collectionapi.metmuseum.org/public/collection/v1/search?q=cat&hasImages=true",
    ]:
        try:
            d = get(url)
            log(f"  OK  total={d.get('total')}  <- {url.split('?')[1][:60]}")
        except urllib.error.HTTPError as e:
            log(f"  HTTP {e.code} <- {url.split('?')[1][:60]}")
    o = get("https://collectionapi.metmuseum.org/public/collection/v1/objects/45734")
    log(f"  藏品详情字段({len(o)}): {sorted(o.keys())}")
    for k in ("objectID", "title", "culture", "country", "objectDate",
              "medium", "department", "classification", "accessionYear"):
        log(f"    {k}: {str(o.get(k))[:70]}")


# ------------------------------------------------------ WALS row counts
def wals_rows():
    base = "https://raw.githubusercontent.com/cldf-datasets/wals/main/cldf/"
    # raw.githubusercontent was reported unreachable; use the API instead if needed
    for name in ["values.csv", "languages.csv", "parameters.csv"]:
        try:
            raw = get(base + name, as_json=False)
            text = raw.decode("utf-8", "replace")
            rows = list(csv.reader(io.StringIO(text)))
            log(f"  {name:<18} {len(raw):>9} B  数据行 = {len(rows) - 1}")
            log(f"     表头: {rows[0][:14]}")
        except Exception as e:  # noqa: BLE001
            log(f"  {name}: {type(e).__name__} {str(e)[:80]}")


# ------------------------------------------------------ Steam
def steam():
    d = get("https://api.steampowered.com/ISteamApps/GetAppList/v2/")
    apps = d["applist"]["apps"]
    log(f"  Steam 全量 App 数 = {len(apps)}")
    log(f"  样例: {apps[:2]}")
    # store detail for one app
    s = get("https://store.steampowered.com/api/appdetails?appids=570&cc=us&l=en")
    det = (s.get("570") or {}).get("data") or {}
    log(f"  appdetails 字段({len(det)}): {sorted(det.keys())[:30]}")
    for k in ("name", "release_date", "price_overview", "genres", "developers",
              "publishers", "categories", "platforms"):
        log(f"    {k}: {str(det.get(k))[:90]}")


# ------------------------------------------------------ BoardGameGeek
def bgg():
    raw = get("https://boardgamegeek.com/xmlapi2/thing?id=13,1,2&stats=1",
              as_json=False)
    text = raw.decode("utf-8", "replace")
    log(f"  BGG XML 字节数 = {len(text)}")
    log(f"  含 <item>: {text.count('<item')}  含 <name: {text.count('<name')}")
    log(f"  片段: {text[:300]}")


# ------------------------------------------------------ economy options
def comtrade():
    d = get("https://comtradeapi.un.org/public/v1/preview/C/A/HS"
            "?reporterCode=156&period=2022&cmdCode=85&flowCode=X")
    log(f"  UN Comtrade 响应 keys = {list(d.keys())[:8]}")
    log(f"  count = {d.get('count')}")
    data = d.get("data") or []
    if data:
        log(f"  记录字段({len(data[0])}): {sorted(data[0].keys())}")


def worldbank():
    d = get("https://api.worldbank.org/v2/country/CHN/indicator/"
            "NY.GDP.PCAP.CD?format=json&per_page=5")
    log(f"  元数据: {d[0]}")
    log(f"  样例: {d[1][0] if len(d) > 1 else None}")


def patentsview():
    d = get("https://search.patentsview.org/api/v1/patent/?q={}&f=[]&o=[]",
            headers={"Accept": "application/json"})
    log(f"  keys = {list(d.keys())[:8]}")


probe("1. Met API：搜索端点与藏品详情字段", met_search)
probe("2. WALS CLDF：CSV 实际行数", wals_rows)
probe("3. Steam：游戏数量与详情字段（经济+文化）", steam)
probe("4. BoardGameGeek：桌游数据库（文化+经济）", bgg)
probe("5. UN Comtrade：国际贸易（经济）", comtrade)
probe("6. World Bank API（经济）", worldbank)
probe("7. PatentsView：专利 API（经济）", patentsview)

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
