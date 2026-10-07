# -*- coding: utf-8 -*-
"""Step 04 - fetch Chinese labels so the UI can offer a zh/en switch.

Sources:
  * Wikidata zh labels for languages, keyed by ISO 639-3 (P220) and
    Glottolog code (P1394)
  * a small hand-written dictionary for WALS macroareas (6) and the most
    common language families, which have no convenient machine source

Output: data/raw/xref/zh_labels.json

WDQS is degraded (~1 req/min), so this makes only two queries and caches them.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (
    PROCESSED, XREF_DIR, banner, exists, human, log, read_json, wdqs, write_json,
)

OUT = os.path.join(XREF_DIR, "zh_labels.json")
# 前端要读，所以也放一份到 processed/（Vite 只挂载 /data，两处都能取到）
OUT_PUBLISHED = os.path.join(PROCESSED, "zh_labels.json")

# 语区只有 6 个，直接手写
MACRO_ZH = {
    "Africa": "非洲",
    "Eurasia": "欧亚",
    "Papunesia": "巴布亚新几内亚区",
    "North America": "北美",
    "South America": "南美",
    "Australia": "澳洲",
}

# 语系名称 WALS 用的是英文，挑选覆盖语言数最多的一批给出中文
FAMILY_ZH = {
    "Niger-Congo": "尼日尔-刚果语系",
    "Austronesian": "南岛语系",
    "Indo-European": "印欧语系",
    "Sino-Tibetan": "汉藏语系",
    "Afro-Asiatic": "亚非语系",
    "Pama-Nyungan": "帕马-尼永干语系",
    "Trans-New Guinea": "跨新几内亚语系",
    "Oto-Manguean": "奥托-曼格语系",
    "Altaic": "阿尔泰语系",
    "Austro-Asiatic": "南亚语系",
    "Eastern Sudanic": "东苏丹语系",
    "Uto-Aztecan": "犹他-阿兹特克语系",
    "Algic": "阿尔冈昆语系",
    "Nilo-Saharan": "尼罗-撒哈拉语系",
    "Sino-Tibetan ": "汉藏语系",
    "Uralic": "乌拉尔语系",
    "Dravidian": "达罗毗荼语系",
    "Tai-Kadai": "侗台语系",
    "Hmong-Mien": "苗瑶语系",
    "Tupi": "图皮语系",
    "Carib": "加勒比语系",
    "Arawakan": "阿拉瓦克语系",
    "Quechuan": "克丘亚语系",
    "Mayan": "玛雅语系",
    "Turkic": "突厥语系",
    "Mongolic": "蒙古语系",
    "Tungusic": "通古斯语系",
    "Japanese": "日语系",
    "Korean": "朝鲜语系",
    "Kartvelian": "卡特维尔语系",
    "Northwest Caucasian": "西北高加索语系",
    "Northeast Caucasian": "东北高加索语系",
    "Basque": "巴斯克语系",
    "Chukotko-Kamchatkan": "楚科奇-堪察加语系",
    "Eskimo-Aleut": "爱斯基摩-阿留申语系",
    "Na-Dene": "纳-德内语系",
    "Salishan": "萨利什语系",
    "Siouan": "苏语系",
    "Iroquoian": "易洛魁语系",
    "Muskogean": "马斯科吉语系",
    "Athapaskan": "阿萨巴斯卡语系",
    "other": "其他",
}


def fetch_by_property(prop: str, label: str) -> dict[str, str]:
    """按属性取标签，**优先简体**。

    只取 `zh` 会繁简混杂：实测 "保加利亞語 / 捷克語 / 荷蘭語" 是繁体，
    而 "德语 / 法语" 是简体，界面上会很乱。所以把几种中文标签都取回来，
    按 zh-hans > zh-cn > zh > zh-hant > zh-tw 的优先级挑。
    """
    q = f"""
SELECT ?code ?lang ?zh WHERE {{
  ?item wdt:{prop} ?code ; rdfs:label ?zh .
  BIND(lang(?zh) AS ?lang)
  FILTER(?lang IN ("zh-hans", "zh-cn", "zh", "zh-hant", "zh-tw", "zh-hk"))
}}
"""
    log(f"  查询 {label} ({prop}) …")
    rows = wdqs(q)
    # 优先级：数值越小越优先
    PRIORITY = {"zh-hans": 0, "zh-cn": 1, "zh": 2, "zh-hant": 3, "zh-tw": 4, "zh-hk": 5}
    best: dict[str, tuple[int, str]] = {}
    for r in rows:
        code = r["code"]["value"].strip().lower()
        lang = r["lang"]["value"].strip()
        zh = r["zh"]["value"].strip()
        if not code or not zh:
            continue
        rank = PRIORITY.get(lang, 9)
        cur = best.get(code)
        if cur is None or rank < cur[0]:
            best[code] = (rank, zh)
    out = {k: v[1] for k, v in best.items()}
    trad = sum(1 for k, (rk, _) in best.items() if rk >= 3)
    log(f"    得到 {human(len(out))} 条（其中仅繁体可得 {human(trad)} 条）")
    return out


def fetch_families() -> dict[str, str]:
    """语系英文名 -> 中文名。WALS 的语系名（如 Niger-Congo）与 Wikidata 的
    英文标签常有连字符差异，所以做一次归一化后再匹配。"""
    q = """
SELECT ?en ?zh WHERE {
  ?item wdt:P31/wdt:P279* wd:Q25295 ;
        rdfs:label ?en ; rdfs:label ?zh .
  FILTER(lang(?en) = "en")
  FILTER(lang(?zh) IN ("zh-hans", "zh-cn", "zh"))
} LIMIT 4000
"""
    log("  查询语系名称 …")
    rows = wdqs(q)
    out: dict[str, str] = {}
    for r in rows:
        en = r["en"]["value"].strip()
        zh = r["zh"]["value"].strip()
        if en and zh:
            out[_norm(en)] = zh
    log(f"    得到 {human(len(out))} 条")
    return out


def _norm(s: str) -> str:
    """归一化：统一各种连字符与空白，便于跨源匹配。"""
    for ch in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        s = s.replace(ch, "-")
    return " ".join(s.split()).strip().lower()


def wals_family_names() -> list[str]:
    """WALS 实际用到的语系名（用它决定要给哪些语系补中文）。"""
    import csv

    p = os.path.join(os.path.dirname(XREF_DIR), "wals", "languages.csv")
    if not os.path.exists(p):
        log(f"    !! 找不到 {p}，跳过语系长尾补充")
        return []
    names: set[str] = set()
    with open(p, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            fam = (row.get("Family") or "").strip()
            if fam:
                names.add(fam)
    return sorted(names)


def publish(payload: dict) -> None:
    """写到 raw（缓存）与 processed（前端读取）两处。"""
    write_json(OUT, payload)
    write_json(OUT_PUBLISHED, payload)


def main() -> None:
    banner("抓取中文标签")
    if exists(OUT) and "--force" not in sys.argv:
        log(f"  已缓存：{OUT}")
        # 缓存存在但前端那份可能缺失（例如首次运行后补跑）
        if not exists(OUT_PUBLISHED):
            publish(read_json(OUT))
            log(f"  已补写前端用的一份 -> {OUT_PUBLISHED}")
        return

    by_iso3: dict[str, str] = {}
    by_glotto: dict[str, str] = {}
    try:
        by_iso3 = fetch_by_property("P220", "ISO 639-3")
    except Exception as exc:  # noqa: BLE001
        log(f"  ISO 639-3 查询失败：{type(exc).__name__}: {str(exc)[:80]}")
    try:
        by_glotto = fetch_by_property("P1394", "Glottolog")
    except Exception as exc:  # noqa: BLE001
        log(f"  Glottolog 查询失败：{type(exc).__name__}: {str(exc)[:80]}")

    # 语系：先用手写表，再用 Wikidata 补长尾
    families = dict(FAMILY_ZH)
    try:
        wd_fam = fetch_families()
        added = 0
        for en_name in wals_family_names():
            if en_name in families:
                continue
            zh_name = wd_fam.get(_norm(en_name))
            if zh_name:
                families[en_name] = zh_name
                added += 1
        log(f"    语系长尾补充 {human(added)} 条")
    except Exception as exc:  # noqa: BLE001
        log(f"  语系查询失败：{type(exc).__name__}: {str(exc)[:80]}")

    publish({
        "by_iso639p3": by_iso3,
        "by_glottocode": by_glotto,
        "macroarea": MACRO_ZH,
        "family": families,
    })
    banner("完成")
    log(f"  ISO 639-3 中文名 = {human(len(by_iso3))}")
    log(f"  Glottolog 中文名 = {human(len(by_glotto))}")
    log(f"  语区 = {human(len(MACRO_ZH))}   语系 = {human(len(families))}")
    log(f"  写入 -> {OUT}")
    log(f"        {OUT_PUBLISHED}")


if __name__ == "__main__":
    main()
