# -*- coding: utf-8 -*-
"""Step 02 - fetch Wikimedia monthly time series for every language edition.

  * pageviews  -> data/raw/wikimedia/pageviews.json
  * edits      -> data/raw/wikimedia/edits.json
  * join table -> data/raw/wikimedia/join.json

Fetches ALL language editions (not only the WALS-joinable ones) so the
"digital vitality" layer stands on its own and future extensions have data.
Resumable: already-collected language codes are skipped.

Usage:
  python 02_fetch_wikimedia.py [--limit N] [--only-joined] [--force]
"""
from __future__ import annotations

import csv
import os
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    WALS_DIR, WIKIMEDIA_DIR, XREF_DIR, banner, exists, http_json, human,
    log, norm_month, read_json, write_json,
)

START = "2015070100"
END = "2026010100"
# The Wikimedia REST API throttles aggressively from this host: 0.2s spacing
# produced HTTP 429 on the majority of requests. 1.5s is sustainable.
DELAY = 1.5
SAVE_EVERY = 10
PV_URL = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/"
          "{proj}/all-access/user/monthly/{start}/{end}")
ED_URL = ("https://wikimedia.org/api/rest_v1/metrics/edits/aggregate/"
          "{proj}/all-editor-types/all-page-types/monthly/{start}/{end}")

PV_OUT = os.path.join(WIKIMEDIA_DIR, "pageviews.json")
ED_OUT = os.path.join(WIKIMEDIA_DIR, "edits.json")
JOIN_OUT = os.path.join(WIKIMEDIA_DIR, "join.json")


# --------------------------------------------------------------------------- setup
def load_editions() -> dict[str, str]:
    """wiki language code -> display name (364 entries)."""
    d = http_json("https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json")
    out: dict[str, str] = {}
    for k, v in d["sitematrix"].items():
        if not k.isdigit():
            continue
        code = (v.get("code") or "").lower()
        for site in v.get("site", []):
            if site.get("code") == "wiki" and site.get("url"):
                out[code] = v.get("name") or code
    return out


def load_wals_index() -> tuple[dict[str, list[dict]], dict[str, int]]:
    """Index WALS languages by ISO code -> *list* of candidate rows.

    Glottocode is NOT unique in WALS (3,573 rows share only 2,502 Glottocodes;
    93 Glottocodes cover 2-6 genuinely different varieties, e.g. swis1247 =
    Alsatian + 5 Swiss German varieties, with conflicting feature values).
    So one ISO code can map to several WALS rows and the caller must choose.
    """
    p = os.path.join(WALS_DIR, "languages.csv")
    with open(p, "r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # how much data does each WALS row actually have? used to pick the richest.
    cov: dict[str, int] = {}
    with open(os.path.join(WALS_DIR, "values.csv"), "r", encoding="utf-8") as fh:
        for v in csv.DictReader(fh):
            cov[v["Language_ID"]] = cov.get(v["Language_ID"], 0) + 1

    by_code: dict[str, list[dict]] = {}
    for r in rows:
        keys = []
        if r.get("ISO639P3code"):
            keys.append(r["ISO639P3code"].strip().lower())
        for tok in (r.get("ISO_codes") or "").replace(";", " ").replace(",", " ").split():
            keys.append(tok.strip().lower())
        for k in keys:
            if k:
                by_code.setdefault(k, []).append(r)
    return by_code, cov


def pick_candidate(cands: list[dict], cov: dict[str, int]) -> tuple[dict, bool]:
    """Choose one WALS row for a wiki edition.

    Preference: the row with the most feature values (richest for the dashboard);
    ties broken by WALS ID so the choice is deterministic. Returns
    (row, ambiguous) where ambiguous means several distinct rows were eligible.
    """
    ranked = sorted(cands, key=lambda r: (-cov.get(r["ID"], 0), r["ID"]))
    return ranked[0], len(ranked) > 1


def build_join() -> tuple[dict[str, dict], dict]:
    """wiki code -> WALS row, using a two-hop ISO lookup."""
    banner("1. 构建 WALS <-> Wikipedia 关联表")
    editions = load_editions()
    by_code, cov = load_wals_index()
    iso1_to_3 = read_json(os.path.join(XREF_DIR, "iso639.json"))
    log(f"  维基语言版本 = {human(len(editions))}")
    log(f"  WALS ISO 索引 = {human(len(by_code))}")
    log(f"  ISO 映射 = {human(len(iso1_to_3))}")

    join: dict[str, dict] = {}
    direct = via_iso = ambiguous = 0
    for code, name in sorted(editions.items()):
        cands: list[dict] | None = None
        hop: str | None = None
        if code in by_code:
            cands, hop = by_code[code], "direct"
            direct += 1
        else:
            iso3 = iso1_to_3.get(code)
            if iso3 and iso3 in by_code:
                cands, hop = by_code[iso3], "iso1->iso3"
                via_iso += 1

        row: dict | None = None
        amb = False
        if cands:
            row, amb = pick_candidate(cands, cov)
            if amb:
                ambiguous += 1

        join[code] = {
            "wiki_code": code,
            "wiki_name": name,
            "joined": cands is not None,
            "hop": hop,
            # wals_id is the unique unit of analysis; glottocode only groups
            "wals_id": (row or {}).get("ID"),
            "glottocode": (row or {}).get("Glottocode"),
            "iso639p3": (row or {}).get("ISO639P3code"),
            "name": (row or {}).get("Name"),
            "macroarea": (row or {}).get("Macroarea"),
            "latitude": (row or {}).get("Latitude"),
            "longitude": (row or {}).get("Longitude"),
            "family": (row or {}).get("Family"),
            "genus": (row or {}).get("Genus"),
            "iso_candidates": len(cands) if cands else 0,
            "join_ambiguous": bool(amb),
        }
    log(f"  直接命中 = {human(direct)}   经 ISO 映射 = {human(via_iso)}   "
        f"合计 = {human(direct + via_iso)}")
    log(f"  未关联 = {human(len(editions) - direct - via_iso)}")
    log(f"  其中 ISO 码对应多个 WALS 条目（已按数据最丰富者择优）= "
        f"{human(ambiguous)}")
    write_json(JOIN_OUT, join)
    log(f"  写入 {JOIN_OUT}")
    return join, {"total": len(editions), "joined": direct + via_iso}


# --------------------------------------------------------------------------- fetch
def fetch_one(url: str, *, retries: int = 6) -> list[dict]:
    """Fetch one metric series. 429 is honoured via Retry-After; 404 is permanent."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            d = http_json(url, timeout=90, retries=1)
            items = d.get("items") or []
            # pageviews: flat items[]; edits: items[0].results[]
            if items and "results" in items[0]:
                return items[0]["results"]
            return items
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                # this wiki has no data for this metric; permanent
                return []
            if exc.code == 429:
                wait = float(exc.headers.get("Retry-After") or 0) or (3.0 * attempt)
                wait = min(wait, 60.0)
                time.sleep(wait)
                last = exc
                continue
            last = exc
            time.sleep(2.0 * attempt)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2.0 * attempt)
    log(f"    FAIL {url.split('/aggregate/')[1][:56]} -> {type(last).__name__}")
    return []


def is_valid_series(series) -> bool:
    """A usable series is a non-empty dict whose keys are all YYYYMM.

    Guards against stale caches written by older code that stored
    ``timestamp[:6]`` on ISO timestamps, producing keys like "2015-0"
    with the month information already lost.
    """
    if not series:
        return False
    return all(isinstance(k, str) and len(k) == 6 and k.isdigit()
               for k in series)


def collect(codes: list[str], label: str, url_tpl: str,
            out_path: str) -> dict[str, dict]:
    banner(f"{label}（{human(len(codes))} 个语言版本）")
    store: dict[str, dict] = {}
    if exists(out_path) and "--force" not in sys.argv:
        store = read_json(out_path)
        stale = sum(1 for v in store.values() if v and not is_valid_series(v))
        if stale:
            log(f"  检测到 {human(stale)} 条月份的键格式非法，将重新抓取")
        log(f"  已有 {human(len(store))} 条，续抓")

    todo = [c for c in codes if not is_valid_series(store.get(c))]
    log(f"  待抓 {human(len(todo))} 条，预计 {len(todo) * (DELAY + 0.35) / 60:.1f} 分钟")

    for i, code in enumerate(todo, 1):
        proj = f"{code}.wikipedia.org"
        items = fetch_one(url_tpl.format(proj=proj, start=START, end=END))
        if items:
            key = "views" if "views" in items[0] else "edits"
            store[code] = {norm_month(it["timestamp"]): it.get(key, 0)
                           for it in items}
        else:
            store[code] = {}
        if i % SAVE_EVERY == 0 or i == len(todo):
            write_json(out_path, store)
            log(f"    {i}/{len(todo)}  {code:<8} "
                f"已存 {human(len(store))} 条")
        time.sleep(DELAY)

    write_json(out_path, store)
    got = sum(1 for v in store.values() if v)
    log(f"  完成：{human(got)}/{human(len(store))} 个版本拿到数据 -> {out_path}")
    return store


def main() -> None:
    join, stats = build_join()
    # Order: languages that joined to WALS first, so a partial run still yields
    # the data the dashboard actually needs.
    joined = [c for c in sorted(join) if join[c]["joined"]]
    rest = [c for c in sorted(join) if not join[c]["joined"]]
    codes = joined + rest
    if "--only-joined" in sys.argv:
        codes = joined
    limit = None
    for a in sys.argv:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
    if limit:
        codes = codes[:limit]
    log(f"  抓取顺序：先 {human(len(joined))} 个可关联语言，再 {human(len(rest))} 个其余版本")

    pv = collect(codes, "2. 浏览量时间序列 (pageviews)", PV_URL, PV_OUT)
    ed = collect(codes, "3. 编辑量时间序列 (edits)", ED_URL, ED_OUT)

    banner("4. 汇总")
    log(f"  语言版本总数        : {human(stats['total'])}")
    log(f"  可关联 WALS         : {human(stats['joined'])}")
    log(f"  已抓浏览量          : {human(sum(1 for v in pv.values() if v))}")
    log(f"  已抓编辑量          : {human(sum(1 for v in ed.values() if v))}")
    if pv:
        sample = next((v for v in pv.values() if v), {})
        log(f"  时间点数量          : {human(len(sample))}")


if __name__ == "__main__":
    main()
