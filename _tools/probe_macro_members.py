# -*- coding: utf-8 -*-
"""Probe: does Wikidata link a macrolanguage's ISO 639-3 code to its member
varieties' codes? That would let wiki codes like zh/ar/fa/sw join to WALS,
which lists varieties rather than macrolanguages.

Tries two candidate relations:
  A. ?member wdt:P279+ ?macro   (subclass of)
  B. ?macro  wdt:P527  ?member  (has part)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from common import XREF_DIR, banner, human, log, wdqs, write_json  # noqa: E402

OUT = os.path.join(XREF_DIR, "macro_members.json")

Q_P279 = """
SELECT ?macroIso ?memberIso WHERE {
  ?member wdt:P220 ?memberIso ; wdt:P279+ ?macro .
  ?macro wdt:P220 ?macroIso .
  FILTER(?macroIso != ?memberIso)
} LIMIT 5000
"""

Q_P527 = """
SELECT ?macroIso ?memberIso WHERE {
  ?macro wdt:P220 ?macroIso ; wdt:P527 ?member .
  ?member wdt:P220 ?memberIso .
} LIMIT 5000
"""


def run(name: str, q: str) -> dict[str, list[str]]:
    banner(name)
    try:
        rows = wdqs(q)
    except Exception as exc:  # noqa: BLE001
        log(f"  失败：{type(exc).__name__}: {str(exc)[:110]}")
        return {}
    log(f"  得到 {human(len(rows))} 条")
    out: dict[str, list[str]] = {}
    for r in rows:
        m = r["macroIso"]["value"].strip().lower()
        c = r["memberIso"]["value"].strip().lower()
        if m and c and m != c:
            out.setdefault(m, []).append(c)
    for k in out:
        out[k] = sorted(set(out[k]))
    # 抽查几个我们关心的宏观语言
    for probe in ("zho", "ara", "fas", "swa", "msa", "aze", "srp", "mon", "uzb", "kur", "nep"):
        if probe in out:
            log(f"    {probe} -> {out[probe][:12]}")
    return out


def main() -> None:
    a = run("A. P279+ (subclass of)", Q_P279)
    b = run("B. P527 (has part)", Q_P527)
    merged: dict[str, list[str]] = {}
    for src in (a, b):
        for k, v in src.items():
            merged.setdefault(k, [])
            merged[k] = sorted(set(merged[k]) | set(v))
    banner("汇总")
    log(f"  宏观语言数 = {human(len(merged))}")
    log(f"  成员对总数 = {human(sum(len(v) for v in merged.values()))}")
    for probe in ("zho", "ara", "fas", "swa", "msa", "aze", "srp", "mon", "uzb", "kur", "nep"):
        log(f"    {probe} -> {merged.get(probe, [])[:12]}")
    if merged:
        write_json(OUT, merged)
        log(f"  写入 -> {OUT}")
    else:
        log("  没有拿到可用的映射，需要改用人工表")


if __name__ == "__main__":
    main()
