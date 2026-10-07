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

# 宏观语言（macrolanguage）-> 其下属变体的 ISO 639-3 代码。
#
# 为什么需要：ISO 639-1 -> 639-3 常常给出**宏观语言**代码（zh→zho、ar→ara、fa→fas、sw→swa），
# 而 WALS 收录的是**具体变体**（cmn/arb/pes/swh），所以直接查会全部落空。
# 实测这导致阿拉伯语、波斯语、斯瓦希里语、马来语、蒙古语、汉语等一批主流语言
# 完全没有进入活力层。
#
# 用 P279 **单层**，不要 P279+：传递闭包会把"历史上源自"的语言也算进来 ——
# 实测 ara 的闭包包含 mlt（马耳他语），于是 ar.wikipedia 被错误地关联到马耳他语。
# 单层则 ara -> arb（现代标准阿拉伯语）等真正的成员。
MACRO_QUERY = """
SELECT ?macroIso ?memberIso WHERE {
  ?member wdt:P220 ?memberIso ; wdt:P279 ?macro .
  ?macro wdt:P220 ?macroIso .
  FILTER(?macroIso != ?memberIso)
} LIMIT 5000
"""


def fetch_macro_members() -> None:
    """宏观语言 -> 成员变体代码，写 xref/macro_members.json。"""
    dest = os.path.join(XREF_DIR, "macro_members.json")
    if exists(dest) and not FORCE:
        log(f"  skip  已存在 ({human(os.path.getsize(dest))} B)")
        return
    log("  查询 WDQS（限流约 1 次/分钟）...")
    rows = wdqs(MACRO_QUERY)
    out: dict[str, list[str]] = {}
    for r in rows:
        macro = r["macroIso"]["value"].strip().lower()
        member = r["memberIso"]["value"].strip().lower()
        if macro and member and macro != member:
            out.setdefault(macro, [])
            if member not in out[macro]:
                out[macro].append(member)
    for k in out:
        out[k] = sorted(out[k])
    write_json(dest, out)
    log(f"  ok    宏观语言 {human(len(out))} 个，成员对 "
        f"{human(sum(len(v) for v in out.values()))} 组 -> {dest}")


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
    fetch_macro_members()
    banner("完成")
    log(f"  WALS  -> {WALS_DIR}")
    log(f"  XREF  -> {XREF_DIR}")


if __name__ == "__main__":
    main()
