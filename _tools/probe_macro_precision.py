# -*- coding: utf-8 -*-
"""收紧宏观语言关系：P279+ 的传递闭包过贪（把 ar -> mlt 马耳他语都算进来了）。

对比三种关系的精确度：
  P279+  传递闭包（当前，过贪）
  P279   单层
  P527   has part（更精确但覆盖少）
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from common import banner, human, log, wdqs  # noqa: E402

QS = {
    "P279 单层": """
SELECT ?macroIso ?memberIso WHERE {
  ?member wdt:P220 ?memberIso ; wdt:P279 ?macro .
  ?macro wdt:P220 ?macroIso .
  FILTER(?macroIso != ?memberIso)
} LIMIT 5000
""",
    "P527 has part": """
SELECT ?macroIso ?memberIso WHERE {
  ?macro wdt:P220 ?macroIso ; wdt:P527 ?member .
  ?member wdt:P220 ?memberIso .
  FILTER(?macroIso != ?memberIso)
} LIMIT 5000
""",
}

PROBE = ("zho", "ara", "fas", "swa", "msa", "aze", "mon", "uzb", "kur", "que", "cre", "iku")


def collect(q):
    rows = wdqs(q)
    out = {}
    for r in rows:
        m = r["macroIso"]["value"].strip().lower()
        c = r["memberIso"]["value"].strip().lower()
        if m and c and m != c:
            out.setdefault(m, set()).add(c)
    return {k: sorted(v) for k, v in out.items()}


def main():
    results = {}
    for name, q in QS.items():
        banner(name)
        try:
            d = collect(q)
        except Exception as exc:  # noqa: BLE001
            log(f"  失败 {type(exc).__name__}: {str(exc)[:100]}")
            d = {}
        results[name] = d
        log(f"  宏观语言 {human(len(d))} 个，成员对 {human(sum(len(v) for v in d.values()))}")
        for p in PROBE:
            if p in d:
                log(f"    {p} -> {d[p][:10]}")

    banner("WALS 里的阿拉伯语 / 波斯语 / 克丘亚语条目")
    import csv
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "raw", "wals", "languages.csv")
    with open(p, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for kw in ("Arabic", "Persian", "Quechua", "Swahili", "Malay", "Mongol"):
        log(f"  --- {kw} ---")
        for r in rows:
            if kw.lower() in r["Name"].lower():
                log(f"    {r['ID']:<6} {r['Name'][:34]:<36} iso={r.get('ISO639P3code',''):<6} "
                    f"glotto={r.get('Glottocode','')}")


if __name__ == "__main__":
    main()
