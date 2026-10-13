# -*- coding: utf-8 -*-
"""Step 06 - fetch Glottolog's AES (Agglomerated Endangerment Status).

**为什么在已有 UNESCO 等级（步骤 05）之后还要这一步：**

UNESCO 名录**只收濒危语言** —— 全名录 2,593 条里只有 82 条是 safe。
所以用 UNESCO 做「濒危程度 × 数字关注度」的分析时，
根本没有"未濒危"这一档作参照，而且 2,662 门语言里只有 1,116 门能匹配上（41.9%）。
这会让散点图严重偏斜。

Glottolog 的 AES 解决了这个问题：它给**所有** languoid 都标了级，
实测 8,672 个条目，其中 2,919 个是 not endangered，
能匹配上本项目 **2,589 / 2,662 = 97.3%** 的语言。这才撑得起散点图。

AES 的 6 级（数值来自 CLDF codes.csv 的 numerical_value，非我方臆定）：
    1 not endangered   EGIDS <=6a ; UNESCO safe      ; ElCat safe
    2 threatened       EGIDS 6b   ; UNESCO vulnerable; ElCat vulnerable
    3 shifting         EGIDS 7    ; UNESCO definitely endangered
    4 moribund         EGIDS 8a
    5 nearly extinct   EGIDS 8b
    6 extinct

数据来源：github.com/glottolog/glottolog-cldf 的 cldf/values.csv（参数 aes）。
`raw.githubusercontent.com` 本机不可达，jsDelivr 又有 20 MB 上限而该文件 21.4 MB，
所以走 GitHub 的 blob API（base64，支持最大 100 MB）。

Output:
  data/raw/glottolog/values.csv    原始 CLDF 值表（缓存，21 MB）
  data/processed/aes.json          前端读取的紧凑查表
"""
from __future__ import annotations

import base64
import csv
import io
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    PROCESSED, RAW, banner, exists, http_get, human, log, write_json,
)

REPO = "glottolog/glottolog-cldf"
DIR = os.path.join(RAW, "glottolog")
VALUES_CACHE = os.path.join(DIR, "values.csv")
CODES_CACHE = os.path.join(DIR, "codes.csv")
OUT = os.path.join(PROCESSED, "aes.json")
JSDELIVR = f"https://cdn.jsdelivr.net/gh/{REPO}@master/cldf/codes.csv"


def fetch_values() -> bytes:
    """values.csv 21.4 MB：jsDelivr 有 20 MB 上限，raw.github 不可达，走 blob API。"""
    if exists(VALUES_CACHE) and os.path.getsize(VALUES_CACHE) > 1_000_000:
        log(f"  已有缓存 {human(os.path.getsize(VALUES_CACHE))} B -> {VALUES_CACHE}")
        return open(VALUES_CACHE, "rb").read()
    os.makedirs(DIR, exist_ok=True)
    meta = json.loads(http_get(
        f"https://api.github.com/repos/{REPO}/contents/cldf/values.csv"))
    size = meta["size"]
    log(f"  文件 {human(size)} B，经 blob API 下载（base64）…")
    blob = json.loads(http_get(
        f"https://api.github.com/repos/{REPO}/git/blobs/{meta['sha']}",
        timeout=600))
    raw = base64.b64decode(blob["content"])
    open(VALUES_CACHE, "wb").write(raw)
    log(f"  下载完成 {human(len(raw))} B -> {VALUES_CACHE}")
    return raw


def fetch_codes() -> str:
    if exists(CODES_CACHE):
        return open(CODES_CACHE, encoding="utf-8").read()
    txt = http_get(JSDELIVR, timeout=120).decode("utf-8")
    os.makedirs(DIR, exist_ok=True)
    open(CODES_CACHE, "w", encoding="utf-8").write(txt)
    return txt


def main() -> None:
    banner("6. 抓取 Glottolog AES 濒危等级（比 UNESCO 覆盖面大得多）")

    codes = list(csv.DictReader(io.StringIO(fetch_codes())))
    aes_codes = [c for c in codes if c["Parameter_ID"] == "aes"]
    levels: dict[str, dict] = {}
    for c in aes_codes:
        # numerical_value 是 CLDF 自带的权威顺序，不是我方臆定的
        nv = (c.get("numerical_value") or "").strip()
        levels[c["ID"]] = {
            "level": int(nv) if nv.isdigit() else None,
            "en": c["Name"],
            "desc": c.get("Description", ""),
        }
    log("  AES 等级（数值取自 CLDF codes.csv 的 numerical_value）：")
    for k in sorted(levels, key=lambda x: levels[x]["level"] or 99):
        v = levels[k]
        log(f"    {v['level']} {v['en']:<16} {v['desc'][:56]}")

    raw = fetch_values()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    log(f"  values.csv 共 {human(len(rows))} 行")

    by_glotto: dict[str, int] = {}
    by_glotto_code: dict[str, str] = {}
    for r in rows:
        if r.get("Parameter_ID") != "aes":
            continue
        code = r.get("Code_ID") or ""
        info = levels.get(code)
        if not info or info["level"] is None:
            continue
        by_glotto[r["Language_ID"]] = info["level"]
        by_glotto_code[r["Language_ID"]] = code

    from collections import Counter
    log(f"  AES 覆盖 {human(len(by_glotto))} 个 Glottocode，分布：")
    for lv in sorted({v for v in by_glotto.values()}):
        n = sum(1 for v in by_glotto.values() if v == lv)
        zh = {1: "未濒危", 2: "受威胁", 3: "转移中", 4: "垂危", 5: "几近灭绝", 6: "已灭绝"}
        log(f"    {lv} {zh.get(lv, ''):<8} {human(n)}")

    payload = {
        "source": "Glottolog CLDF (cldf/values.csv, parameter 'aes')",
        "note": "AES = Agglomerated Endangerment Status，数字越大越濒危：1 未濒危 … 6 已灭绝",
        "levels": {
            str(v["level"]): {"en": v["en"], "desc": v["desc"],
                              "zh": {1: "未濒危", 2: "受威胁", 3: "转移中",
                                     4: "垂危", 5: "几近灭绝", 6: "已灭绝"}.get(v["level"], v["en"])}
            for v in levels.values() if v["level"] is not None
        },
        "by_glottocode": by_glotto,
        "counts": dict(Counter(by_glotto.values())),
    }
    write_json(OUT, payload)
    log(f"  写入 {OUT}")

    # 与 UNESCO 对照：两者口径差异正好说明为什么必须换成 AES
    uni_path = os.path.join(PROCESSED, "endangerment.json")
    langs_path = os.path.join(PROCESSED, "languages.json")
    if exists(uni_path) and exists(langs_path):
        uni = json.load(open(uni_path, encoding="utf-8"))["by_glottocode"]
        langs = json.load(open(langs_path, encoding="utf-8"))
        aes_hit = sum(1 for l in langs if l.get("glottocode") in by_glotto)
        uni_hit = sum(1 for l in langs if l.get("glottocode") in uni)
        both = [l for l in langs
                if l.get("glottocode") in by_glotto and l.get("glottocode") in uni]
        log(f"  与 UNESCO 对照（本项目 {human(len(langs))} 门语言）：")
        log(f"    AES 命中    = {human(aes_hit)} ({aes_hit / len(langs) * 100:.1f}%)")
        log(f"    UNESCO 命中 = {human(uni_hit)} ({uni_hit / len(langs) * 100:.1f}%)")
        if both:
            safe = sum(1 for l in both if by_glotto[l["glottocode"]] == 1)
            log(f"    两者都命中的 {human(len(both))} 门里，AES 判定为「未濒危」的有 "
                f"{human(safe)} 门 —— 这些在 UNESCO 口径下**根本看不到**")


if __name__ == "__main__":
    main()
