# -*- coding: utf-8 -*-
"""Probe: can Glottolog's classification resolve a macrolanguage to its member
varieties, so ISO 639-1 wiki codes like `zh`/`ar`/`fa`/`sw` can be joined?

Idea: a macrolanguage has a Glottocode (Wikidata P1394). Glottolog's CLDF
ValueTable carries a `classification` path per language. If WALS's variety
glottocode appears under the macrolanguage's path, the join is resolvable.
"""
import base64
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from common import XREF_DIR, banner, github_blob, github_list, human, log  # noqa: E402

OUT = os.path.join(XREF_DIR, "glottolog_classification.json")


def main() -> None:
    banner("1. glottolog-cldf 目录结构")
    try:
        files = github_list("glottolog/glottolog-cldf", "cldf")
        names = [f["name"] for f in files]
        log(f"  {names}")
    except Exception as exc:  # noqa: BLE001
        log(f"  失败：{type(exc).__name__}: {str(exc)[:120]}")
        return

    # languages.csv 里通常有 Classification / Macroarea / Latitude 等列
    banner("2. 取 languages.csv 前几行看列名")
    try:
        raw = github_blob("glottolog/glottolog-cldf", "cldf/languages.csv")
        log(f"  大小 = {human(len(raw))} B")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8", "replace"))))
        log(f"  行数 = {human(len(rows))}")
        log(f"  列名 = {list(rows[0].keys())}")
    except Exception as exc:  # noqa: BLE001
        log(f"  失败：{type(exc).__name__}: {str(exc)[:120]}")
        return

    # 找一条有 Classification 的样本
    key = None
    for cand in ("Classification", "classification", "Path", "Family"):
        if cand in rows[0]:
            key = cand
            break
    if key:
        log(f"  使用列 '{key}'")
        shown = 0
        for r in rows:
            if r.get(key):
                log(f"    {r.get('ID')} {r.get('Name')}: {r[key][:110]}")
                shown += 1
                if shown >= 4:
                    break
    else:
        log("  没有谱系列，需要改用 classification.nex 或 ValueTable")

    # 关键验证：标准阿拉伯语(arb) 的谱系里有没有 Arabic(arab1395)
    banner("3. 关键验证：宏观语言能否通过谱系找到变体")
    if key:
        TARGETS = {
            "arab1395": "Arabic (macrolanguage)",
            "stan1318": "Standard Arabic (variety)",
            "mand1415": "Mandarin (variety)",
            "chin1272": "Chinese (macrolanguage)",
            "nucl1301": "Persian?",
        }
        idx = {r.get("ID"): r for r in rows}
        for g, label in TARGETS.items():
            r = idx.get(g)
            if not r:
                log(f"  {label:<32} glottocode={g} 不在表里")
                continue
            path = r.get(key, "")
            log(f"  {label:<32} {g}")
            log(f"      path = {path[:150]}")
    else:
        log("  跳过（没有谱系列）")


if __name__ == "__main__":
    main()
