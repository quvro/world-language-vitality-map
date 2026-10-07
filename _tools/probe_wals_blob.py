# -*- coding: utf-8 -*-
"""Can we fetch the WALS CSVs through api.github.com's blob API (works when
github.com / raw.githubusercontent.com are blocked)?"""
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
OUT_FILE = os.path.join(OUT, "wals_blob.txt")
UA = "Mozilla/5.0 (compatible; CourseProjectProbe/1.0)"
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:210], flush=True)
    except Exception:  # noqa: BLE001
        pass


def get(url, timeout=180, as_json=True):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw


REPO = "cldf-datasets/wals"
listing = get(f"https://api.github.com/repos/{REPO}/contents/cldf")
by_name = {f["name"]: f for f in listing}

for name in ["values.csv", "languages.csv", "parameters.csv",
             "genealogy.csv", "codes.csv", "language_names.csv"]:
    meta = by_name.get(name)
    if not meta:
        log(f"  {name}: 不在目录列表里")
        continue
    size = meta["size"]
    try:
        blob = get(meta["git_url"])
        content = base64.b64decode(blob["content"])
        rows = list(csv.reader(io.StringIO(content.decode("utf-8", "replace"))))
        log(f"  {name:<20} {size:>9} B  -> 解码 {len(content):>9} B  "
            f"行数 = {len(rows) - 1}")
        log(f"      表头: {rows[0][:18]}")
        if len(rows) > 1:
            log(f"      样例行: {rows[1][:10]}")
    except urllib.error.HTTPError as e:
        log(f"  {name:<20} {size:>9} B  blob API HTTP {e.code} (超过上限?)")
    except Exception as e:  # noqa: BLE001
        log(f"  {name:<20} {size:>9} B  FAILED {type(e).__name__}: {str(e)[:70]}")

# how many distinct languages / parameters are actually in values.csv?
try:
    blob = get(by_name["values.csv"]["git_url"])
    content = base64.b64decode(blob["content"]).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(content)))
    log("")
    log(f"  values.csv 总行数 = {len(rows)}")
    log(f"  字段 = {list(rows[0].keys())}")
    for key in ("Language_ID", "Parameter_ID", "Value", "Code_ID"):
        if key in rows[0]:
            log(f"  唯一 {key} = {len({r[key] for r in rows})}")
except Exception as e:  # noqa: BLE001
    log(f"  统计失败: {type(e).__name__} {str(e)[:90]}")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_FILE}")
