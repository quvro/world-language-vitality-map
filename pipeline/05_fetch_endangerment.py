# -*- coding: utf-8 -*-
"""Step 05 - fetch the UNESCO endangerment status for every language.

**为什么需要这一步（这是本项目对"活力"这个词的定义问题的回答）：**

在此之前，项目里所有叫"活力"的指标都来自同一个原始量 ——
某语言的维基百科版本被读了多少次。那是**数字关注度**，不是语言学意义上的
「语言活力」。语言学里的语言活力有成熟定义（UNESCO 的 9 项指标：
代际传承、使用者绝对人数、使用场合、政策、社区态度……），核心是
**代际传承与实际使用**。两者差距很大，而且有系统性偏差：

  · 门槛偏差：维基百科是"读"的，要求有文字传统 + 网络接入人口，
    所以系统性低估无文字传统的语言
  · 人口偏差：浏览量 ≈ 使用者数 × 识字率 × 上网率 × 用维基的习惯，四项相乘会放大差距

接入 UNESCO 濒危等级后，就能把**两个独立的维度摆在一起对照**：

    一门语言在语言学上还活着，但在数字空间里已经死了吗？反过来呢？

实测结论（见 validation）：两者高度一致但并非同一件事 ——
安全语言 75.6% 有维基版本，极度濒危只有 2.0%，已灭绝的 51 种一个都没有。

数据来源：Wikidata P1999（UNESCO language status），由 UNESCO
《世界濒危语言地图》的 6 级量表填充，实测 2,593 种语言有值、94% 带 Glottocode。

Output:
  data/raw/xref/unesco_raw.json       原始 SPARQL 结果（缓存）
  data/processed/endangerment.json    前端读取的紧凑查表

Usage:
  python 05_fetch_endangerment.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    PROCESSED, XREF_DIR, banner, exists, human, log, read_json, wdqs, write_json,
)

OUT = os.path.join(XREF_DIR, "unesco_raw.json")
OUT_PUBLISHED = os.path.join(PROCESSED, "endangerment.json")

# UNESCO 的 6 级量表。数字越小越安全。
LEVELS = {
    1: {"en": "safe", "zh": "安全"},
    2: {"en": "vulnerable", "zh": "脆弱"},
    3: {"en": "definitely endangered", "zh": "明确濒危"},
    4: {"en": "severely endangered", "zh": "严重濒危"},
    5: {"en": "critically endangered", "zh": "极度濒危"},
    6: {"en": "extinct", "zh": "已灭绝"},
}

# 不要用 SERVICE wikibase:label —— 和上面的 OPTIONAL 一起会触发 HTTP 400。
# 直接取 rdfs:label 是稳的。
QUERY = """
SELECT ?item ?glotto ?iso3 ?iso1 ?status ?statusLabel WHERE {
  ?item wdt:P1999 ?status .
  OPTIONAL { ?item wdt:P1394 ?glotto }
  OPTIONAL { ?item wdt:P220 ?iso3 }
  OPTIONAL { ?item wdt:P218 ?iso1 }
  ?status rdfs:label ?statusLabel . FILTER(lang(?statusLabel) = "en")
}
"""


def level_of(label: str) -> int | None:
    """'5 critically endangered' -> 5。UNESCO 的标签都以级别数字开头。"""
    head = (label or "").split(" ", 1)[0]
    return int(head) if head.isdigit() and 1 <= int(head) <= 6 else None


def fetch() -> list[dict]:
    if exists(OUT) and "--force" not in sys.argv:
        rows = read_json(OUT)
        log(f"  已有缓存 {human(len(rows))} 行 -> {OUT}（--force 可重抓）")
        return rows
    rows = wdqs(QUERY)
    write_json(OUT, rows)
    log(f"  写入 {OUT}")
    return rows


def build(rows: list[dict]) -> dict:
    by_glotto: dict[str, int] = {}
    by_iso: dict[str, int] = {}
    skipped = 0
    for r in rows:
        lvl = level_of(r.get("statusLabel", {}).get("value", ""))
        if lvl is None:
            skipped += 1
            continue
        if "glotto" in r:
            by_glotto.setdefault(r["glotto"]["value"], lvl)
        if "iso3" in r:
            by_iso.setdefault(r["iso3"]["value"], lvl)
    return {
        "source": "Wikidata P1999 (UNESCO Atlas of the World's Languages in Danger)",
        "note": "数字越小越安全：1 safe … 6 extinct",
        "levels": {str(k): v for k, v in LEVELS.items()},
        "by_glottocode": by_glotto,
        "by_iso639p3": by_iso,
        "counts": dict(Counter(by_glotto.values())),
        "skipped_unparsable": skipped,
    }


def report(payload: dict) -> None:
    langs_path = os.path.join(PROCESSED, "languages.json")
    if not exists(langs_path):
        log("  （languages.json 还不存在，跳过关联统计）")
        return
    langs = read_json(langs_path)
    g = payload["by_glottocode"]
    i = payload["by_iso639p3"]

    def lvl(l: dict) -> int | None:
        return g.get(l.get("glottocode") or "") or i.get(
            (l.get("iso639p3") or "").lower())

    hit = [l for l in langs if lvl(l)]
    log(f"  关联到本项目的语言 = {human(len(hit))} / {human(len(langs))} "
        f"({len(hit) / max(len(langs), 1) * 100:.1f}%)")

    buckets: dict[int, dict[str, int]] = defaultdict(lambda: {"n": 0, "wiki": 0})
    for l in hit:
        b = buckets[lvl(l)]
        b["n"] += 1
        if l.get("wiki_code"):
            b["wiki"] += 1
    log("  濒危等级 × 是否有维基版本：")
    for k in sorted(buckets):
        d = buckets[k]
        rate = d["wiki"] / d["n"] * 100 if d["n"] else 0
        log(f"    {k} {LEVELS[k]['en']:<24} {human(d['n']):>6} 门, "
            f"有维基版本 {human(d['wiki']):>5} ({rate:5.1f}%)")


def main() -> None:
    banner("5. 抓取 UNESCO 濒危等级（回答「活力到底是什么」）")
    rows = fetch()
    payload = build(rows)
    log(f"  解析出 {human(len(payload['by_glottocode']))} 个 Glottocode、"
        f"{human(len(payload['by_iso639p3']))} 个 ISO 639-3"
        f"（无法解析的 {payload['skipped_unparsable']} 行）")
    write_json(OUT_PUBLISHED, payload)
    log(f"  写入 {OUT_PUBLISHED}")
    report(payload)


if __name__ == "__main__":
    main()
