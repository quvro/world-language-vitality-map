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
import datetime as dt
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


def last_complete_month(today: dt.date | None = None) -> str:
    """最后一个**完整**自然月（YYYYMM）。

    当月的数据是不完整的（API 会返回进行中的部分月份），所以取上一个月。
    这里原本写死成 "2026010100"，结果随着时间推移数据越来越旧却毫无提示 ——
    实测到了 2026-10 才发现白丢了 8 个月（API 上其实有到 2026-09 的数据），
    而界面上还把 2026-01 标成"当前月份"。改成动态计算。
    需要固定区间复现时用环境变量 WIKI_END_MONTH=YYYYMM 覆盖。
    """
    d = today or dt.date.today()
    prev = d.replace(day=1) - dt.timedelta(days=1)
    return prev.strftime("%Y%m")


def next_month(ym: str) -> str:
    """'202601' -> '202602'"""
    y, m = int(ym[:4]), int(ym[4:6])
    m += 1
    if m > 12:
        y, m = y + 1, 1
    return f"{y}{m:02d}"


TARGET_LAST_MONTH = os.environ.get("WIKI_END_MONTH") or last_complete_month()
END = f"{TARGET_LAST_MONTH}0100"
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
def load_editions() -> dict[str, dict]:
    """wiki 语言代码 -> {name, host}。

    **必须用 sitematrix 给的 url，不能拿语言代码拼域名。**
    实测有 7 个版本的域名与语言代码不一致，拼出来会 404：
        yue -> zh-yue.wikipedia.org        （粤语）
        nan -> zh-min-nan.wikipedia.org    （闽南语）
        lzh -> zh-classical.wikipedia.org  （文言文）
        gsw -> als.wikipedia.org           （阿勒曼尼语）
        rup -> roa-rup.wikipedia.org
        sgs -> bat-smg.wikipedia.org
        vro -> fiu-vro.wikipedia.org
    这曾经导致粤语、闽南语等完全没有时间序列数据（抓取时静默 404）。
    """
    d = http_json("https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json")
    out: dict[str, dict] = {}
    for k, v in d["sitematrix"].items():
        if not k.isdigit():
            continue
        code = (v.get("code") or "").lower()
        for site in v.get("site", []):
            if site.get("code") == "wiki" and site.get("url"):
                host = (site["url"].replace("https://", "")
                        .replace("http://", "").rstrip("/"))
                out[code] = {"name": v.get("name") or code, "host": host}
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


def pick_macro_member(member_codes: list[str], by_code: dict[str, list[dict]],
                      cov: dict[str, int]) -> tuple[dict | None, int]:
    """从宏观语言的成员变体里挑一个最合适的。

    排序规则（依次）：
      1. 名称含 "Standard" 的优先 —— 维基百科的宏观语言版本通常用**标准语**书写，
         例如 ar.wikipedia 用现代标准阿拉伯语，WALS 里叫 "Arabic (Modern Standard)"
      2. 名称**不含括号**的优先 —— "Mandarin" 优于 "Kunming"
      3. WALS 特征数据更丰富的优先
      4. wals_id 字典序，保证确定性

    残余歧义（成员都带括号且无标准语标记的，如 que、iku）无法靠规则消除，
    因此结果里会记录 join_ambiguous 与最终选中的 iso 码，便于复核。
    """
    cands: dict[str, dict] = {}
    for mc in member_codes:
        for row in by_code.get(mc, []):
            cands[row["ID"]] = row
    if not cands:
        return None, 0

    def rank(r: dict):
        nm = r["Name"]
        standard = 0 if "standard" in nm.lower() else 1
        paren = 1 if "(" in nm else 0
        return (standard, paren, -cov.get(r["ID"], 0), r["ID"])

    return sorted(cands.values(), key=rank)[0], len(cands)


def build_join(editions: dict[str, dict]) -> tuple[dict[str, dict], dict]:
    """wiki code -> WALS row, three hops: direct / ISO 639-1 / macrolanguage."""
    banner("1. 构建 WALS <-> Wikipedia 关联表")
    by_code, cov = load_wals_index()
    iso1_to_3 = read_json(os.path.join(XREF_DIR, "iso639.json"))
    macro_path = os.path.join(XREF_DIR, "macro_members.json")
    macro_members = read_json(macro_path) if exists(macro_path) else {}
    log(f"  维基语言版本 = {human(len(editions))}")
    log(f"  WALS ISO 索引 = {human(len(by_code))}")
    log(f"  ISO 映射 = {human(len(iso1_to_3))}")
    log(f"  宏观语言表 = {human(len(macro_members))}（缺失则第三跳失效）")

    join: dict[str, dict] = {}
    direct = via_iso = via_macro = ambiguous = 0
    for code, meta_ed in sorted(editions.items()):
        name = meta_ed["name"]
        cands: list[dict] | None = None
        hop: str | None = None
        macro_from: str | None = None
        if code in by_code:
            cands, hop = by_code[code], "direct"
            direct += 1
        else:
            iso3 = iso1_to_3.get(code)
            if iso3 and iso3 in by_code:
                cands, hop = by_code[iso3], "iso1->iso3"
                via_iso += 1
            elif iso3 and iso3 in macro_members:
                # ISO 639-1 给的是宏观语言码（zh/ar/fa/sw…），
                # 而 WALS 只收具体变体（cmn/arb/pes/swh）—— 这里解析下去
                row_m, n_members = pick_macro_member(macro_members[iso3], by_code, cov)
                if row_m is not None:
                    via_macro += 1
                    if n_members > 1:
                        ambiguous += 1
                    join[code] = {
                        "wiki_code": code, "wiki_name": name,
                        "wiki_host": meta_ed["host"],
                        "joined": True, "hop": "macro",
                        "wals_id": row_m.get("ID"),
                        "glottocode": row_m.get("Glottocode"),
                        "iso639p3": row_m.get("ISO639P3code"),
                        "name": row_m.get("Name"),
                        "macroarea": row_m.get("Macroarea"),
                        "latitude": row_m.get("Latitude"),
                        "longitude": row_m.get("Longitude"),
                        "family": row_m.get("Family"),
                        "genus": row_m.get("Genus"),
                        "iso_candidates": n_members,
                        "join_ambiguous": n_members > 1,
                        "macro_from": iso3,
                    }
                    continue

        row: dict | None = None
        amb = False
        if cands:
            row, amb = pick_candidate(cands, cov)
            if amb:
                ambiguous += 1

        join[code] = {
            "wiki_code": code,
            "wiki_name": name,
            "wiki_host": meta_ed["host"],
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
            "macro_from": macro_from,
        }

    total = direct + via_iso + via_macro
    log(f"  直接命中 = {human(direct)}")
    log(f"  经 ISO 639-1 -> 639-3 命中 = {human(via_iso)}")
    log(f"  经宏观语言回退命中 = {human(via_macro)}   <- 接上 zh/ar/fa/sw 等")
    log(f"  合计 = {human(total)}   未关联 = {human(len(editions) - total)}")
    log(f"  其中多候选（已按规则择优）= {human(ambiguous)}")
    write_json(JOIN_OUT, join)
    log(f"  写入 {JOIN_OUT}")
    return join, {"total": len(editions), "joined": total}


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


def probe_last_month(url_tpl: str, editions: dict[str, dict]) -> str:
    """探一下**该指标**实际能取到哪个月。

    必要性：编辑量比浏览量晚约一个月（实测浏览量已到 202609 时编辑量只到 202608）。
    若两个指标都用同一个目标月份判断「是否已覆盖」，
    那么"没到目标"对编辑量永远成立，于是每次运行都会把 364 个版本的
    编辑量全部重抓一遍（每次约 9 分钟），白白浪费。
    用一个内容较多的版本探一次即可，代价是每次运行多 1 个请求。
    """
    for code in ("en", "de", "fr", "es", "ru", "zh"):
        if code not in editions:
            continue
        items = fetch_one(url_tpl.format(
            proj=editions[code]["host"], start=START, end=END))
        if items:
            key = "views" if "views" in items[0] else "edits"
            months = [norm_month(it["timestamp"]) for it in items]
            if months:
                return max(months)
    return TARGET_LAST_MONTH


def collect(codes: list[str], label: str, url_tpl: str,
            out_path: str, editions: dict[str, dict]) -> dict[str, dict]:
    banner(f"{label}（{human(len(codes))} 个语言版本）")
    store: dict[str, dict] = {}
    force = "--force" in sys.argv
    if exists(out_path) and not force:
        store = read_json(out_path)
        stale = sum(1 for v in store.values() if v and not is_valid_series(v))
        if stale:
            log(f"  检测到 {human(stale)} 条月份的键格式非法，将重新抓取")
        log(f"  已有 {human(len(store))} 条，续抓")

    want = probe_last_month(url_tpl, editions)
    log(f"  目标区间 {START[:6]} .. {want}"
        f"{'（该指标可达月份）' if want != TARGET_LAST_MONTH else ''}")

    def shortfall(code: str):
        """返回 None 表示已覆盖到目标月份；'all' 表示要全量抓；否则是要补的起始月。

        只判断"序列非空"是不够的 —— 那样把目标区间往后推时，
        已有的旧序列会被当成有效数据直接跳过，于是数据永远停在旧月份。
        """
        s = store.get(code)
        if force or not is_valid_series(s):
            return "all"
        last = max(s)
        return None if last >= want else last

    plans = [(c, shortfall(c)) for c in codes]
    todo = [(c, m) for c, m in plans if m is not None]
    delta = [(c, m) for c, m in todo if m != "all"]
    log(f"  待抓 {human(len(todo))} 条"
        f"（其中增量补抓 {human(len(delta))} 条，全量 {human(len(todo) - len(delta))} 条），"
        f"预计 {len(todo) * (DELAY + 0.35) / 60:.1f} 分钟")

    for i, (code, miss) in enumerate(todo, 1):
        # 用 sitematrix 的**真实域名**，不要拿语言代码拼（yue/nan/lzh/gsw/rup/sgs/vro 会 404）
        proj = editions[code]["host"]
        # 已有数据的只补缺口，从最后一个月的下一个月开始
        start = START if miss == "all" else f"{next_month(miss)}0100"
        items = fetch_one(url_tpl.format(proj=proj, start=start, end=END))
        if items:
            key = "views" if "views" in items[0] else "edits"
            fresh = {norm_month(it["timestamp"]): it.get(key, 0) for it in items}
            if miss == "all":
                store[code] = fresh
            else:
                store[code] = {**store.get(code, {}), **fresh}
        elif miss == "all":
            # 该版本确实没有数据（404）。补抓返回空时不动原有数据，避免把好数据抹掉
            store[code] = {}
        if i % SAVE_EVERY == 0 or i == len(todo):
            write_json(out_path, store)
            log(f"    {i}/{len(todo)}  {code:<8} "
                f"已存 {human(len(store))} 条")
        time.sleep(DELAY)

    write_json(out_path, store)
    got = sum(1 for v in store.values() if v)
    covered = sum(1 for v in store.values() if v and max(v) >= want)
    log(f"  完成：{human(got)}/{human(len(store))} 个版本拿到数据，"
        f"其中 {human(covered)} 个覆盖到 {want} -> {out_path}")
    return store


def main() -> None:
    editions = load_editions()
    join, stats = build_join(editions)
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

    pv = collect(codes, "2. 浏览量时间序列 (pageviews)", PV_URL, PV_OUT,
                 editions)
    ed = collect(codes, "3. 编辑量时间序列 (edits)", ED_URL, ED_OUT,
                 editions)

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
