# -*- coding: utf-8 -*-
"""Can WALS (language structure) be joined to Wikimedia (time series)?

The whole project hinges on this join. Measures the real overlap.
"""
import base64
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
OUT_FILE = os.path.join(OUT, "join_probe.txt")
UA = "CourseProjectProbe/1.0 (student research; contact: none)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:210], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url, timeout=120, as_json=True, ua=UA):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw


# --- 1. Wikipedia language editions -----------------------------------------
log("=" * 78)
log("### 1. 维基百科语言版本")
sm = get("https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json")
editions = {}
for k, v in sm["sitematrix"].items():
    if not k.isdigit():
        continue
    code = v.get("code")
    for site in v.get("site", []):
        if site.get("code") == "wiki" and site.get("url"):
            editions[code] = v.get("name")
log(f"  语言版本数 = {len(editions)}")
log(f"  代码样例 = {sorted(editions)[:30]}")

# --- 2. article counts for a sample (siteinfo statistics) -------------------
log("")
log("### 2. 条目数（siteinfo statistics 是否可用）")
for lang in ["de", "ja", "sw", "zh", "en"]:
    try:
        d = get(f"https://{lang}.wikipedia.org/w/api.php?action=query&meta=siteinfo"
                f"&siprop=statistics&format=json")
        st = d["query"]["statistics"]
        log(f"  {lang}: articles={st.get('articles'):,}  edits={st.get('edits'):,}  "
            f"users={st.get('users'):,}")
    except Exception as e:  # noqa: BLE001
        log(f"  {lang}: {type(e).__name__} {str(e)[:60]}")

# --- 3. another time series: monthly edits ---------------------------------
log("")
log("### 3. 月度编辑量时间序列（edits 端点）")
try:
    d = get("https://wikimedia.org/api/rest_v1/metrics/edits/aggregate/"
            "de.wikipedia.org/all-editor-types/all-page-types/monthly/"
            "2016010100/2026010100")
    items = d.get("items") or []
    log(f"  de.wikipedia 月数 = {len(items)}")
    if items:
        log(f"  字段 = {sorted(items[0].keys())}")
        log(f"  首月 = {items[0]}")
except Exception as e:  # noqa: BLE001
    log(f"  FAILED {type(e).__name__}: {str(e)[:120]}")

# --- 4. WALS language codes (via GitHub blob API) --------------------------
log("")
log("### 4. WALS 语言表")
listing = get("https://api.github.com/repos/cldf-datasets/wals/contents/cldf")
by_name = {f["name"]: f for f in listing}
blob = get(by_name["languages.csv"]["git_url"])
content = base64.b64decode(blob["content"]).decode("utf-8", "replace")
rows = list(csv.DictReader(io.StringIO(content)))
log(f"  languages.csv 行数 = {len(rows)}")
log(f"  字段 = {list(rows[0].keys())}")

wals_codes: set[str] = set()
for r in rows:
    if r.get("ISO639P3code"):
        wals_codes.add(r["ISO639P3code"].strip().lower())
    for f in ("ISO_codes",):
        for tok in (r.get(f) or "").replace(";", " ").replace(",", " ").split():
            wals_codes.add(tok.strip().lower())
log(f"  WALS 可用的语言代码数 = {len(wals_codes)}")

# --- 5. the join ------------------------------------------------------------
log("")
log("### 5. JOIN 结果")
wiki_codes = {c.lower() for c in editions}
overlap = wiki_codes & wals_codes
log(f"  维基版本代码 {len(wiki_codes)}  ∩  WALS 代码 {len(wals_codes)}  =  "
    f"**{len(overlap)}** 个语言可直接连上")
log(f"  可连接样例 = {sorted(overlap)[:40]}")
missing = sorted(wiki_codes - wals_codes)
log(f"  维基有但 WALS 代码对不上的（前 40）= {missing[:40]}")
log(f"  对不上的一共 {len(missing)} 个")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
