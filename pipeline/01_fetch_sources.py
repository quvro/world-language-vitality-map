# -*- coding: utf-8 -*-
"""Step 01 - fetch the static sources.

  * WALS CLDF tables (6 CSVs)          -> data/raw/wals/
  * Wikidata ISO 639-1 <-> 639-3 xref  -> data/raw/xref/iso639.json

Idempotent: existing non-empty files are skipped unless --force is passed.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    WALS_DIR, WALS_FILES, XREF_DIR, banner, exists, github_blob, human,
    log, wdqs, write_bytes, write_json,
)

FORCE = "--force" in sys.argv

WALS_REPO = "cldf-datasets/wals"
WALS_PATH = "cldf"


def fetch_wals() -> None:
    banner("1. WALS CLDF 四表 + 谱系 + 别名")
    for name in WALS_FILES:
        dest = os.path.join(WALS_DIR, name)
        if exists(dest) and not FORCE:
            log(f"  skip  {name:<20} 已存在 ({human(os.path.getsize(dest))} B)")
            continue
        log(f"  fetch {name} ...")
        data = github_blob(WALS_REPO, f"{WALS_PATH}/{name}")
        write_bytes(dest, data)
        log(f"  ok    {name:<20} {human(len(data))} B")

    # sanity: how many rows did we actually get?
    import csv
    for name in WALS_FILES:
        p = os.path.join(WALS_DIR, name)
        with open(p, "r", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        log(f"    {name:<20} 行数 = {human(len(rows) - 1)}")


ISO_QUERY = """
SELECT ?iso1 ?iso3 WHERE {
  ?item wdt:P218 ?iso1 ; wdt:P220 ?iso3 .
}
"""


def fetch_iso_xref() -> None:
    banner("2. Wikidata ISO 639-1 <-> 639-3 映射")
    dest = os.path.join(XREF_DIR, "iso639.json")
    if exists(dest) and not FORCE:
        log(f"  skip  已存在 ({human(os.path.getsize(dest))} B)")
        return

    log("  查询 WDQS（限流约 1 次/分钟，只跑一次然后缓存）...")
    rows = wdqs(ISO_QUERY)
    mapping: dict[str, str] = {}
    for r in rows:
        a = r["iso1"]["value"].strip().lower()
        b = r["iso3"]["value"].strip().lower()
        if a and b:
            mapping[a] = b
    write_json(dest, mapping)
    log(f"  ok    写入 {human(len(mapping))} 组映射 -> {dest}")


def main() -> None:
    fetch_wals()
    fetch_iso_xref()
    banner("完成")
    log(f"  WALS  -> {WALS_DIR}")
    log(f"  XREF  -> {XREF_DIR}")


if __name__ == "__main__":
    main()
