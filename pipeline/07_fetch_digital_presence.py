"""07_fetch_digital_presence.py —— 维基百科之外的第二个/第三个「数字在场」维度。

用户的要求是：「我希望加入更多和语言濒危程度这方面的数据或者维度，
而不只是维基百科的数据，可以看看有没有该语言热门网站/论坛等等」。

**关于「热门网站 / 论坛」的诚实答复**：Reddit / 贴吧 / Discord / 论坛都没有
可免费批量获取的接口（要 OAuth、要 Key，或直接反爬），这门课的时间预算里
不可靠。所以改用两个**能真正拿到、且学术上站得住**的维度：

  维度 A：**该语言有多少个维基媒体项目**（sitematrix，一次请求）
    一门语言如果只有维基百科，说明它进入数字空间的方式是"被写进百科全书"；
    如果同时还有维基词典、维基文库、维基新闻、维基教科书……说明存在一个
    **持续的编辑者社群**，而不只是被记录的对象。这比"浏览量"更接近"社群厚度"。
    实测 374 个语言版本里，只有 138 个拥有 >= 3 个维基项目。

  维度 B：**Glottolog 的描述文献数（med）**（数据已在本地 values.csv）
    med = "most extensive descriptions" 的条目数，即这门语言有多少份
    长篇描写性文献（语法、词典、词表）。这是**语言学意义上的记录深度**，
    与维基浏览量是完全独立的两个量 —— 正好用来对照「被研究」与「被阅读」。

两个都不需要新下载大文件：A 是一次 HTTP，B 直接读已缓存的 values.csv。

产出 data/processed/digital_presence.json：
    {
      "by_wiki_code": {"en": {"projects": [...], "n": 12, "n_extra": 11}},
      "by_glottocode": {"abkh1242": 3},
      "meta": {...}
    }
"""
import csv
import os
import sys

from common import RAW, PROCESSED, banner, exists, http_json, log, read_json, write_json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SITEMATRIX = ("https://meta.wikimedia.org/w/api.php"
              "?action=sitematrix&format=json&smstate=all")
VALUES_CSV = os.path.join(RAW, "glottolog", "values.csv")
OUT = os.path.join(PROCESSED, "digital_presence.json")
OUT_RAW = os.path.join(RAW, "xref", "sitematrix_raw.json")

# 只统计"内容项目"，跳过 wikispecies / meta / commons 这类多语言共用站点
CONTENT_PROJECTS = {
    "wikipedia", "wiktionary", "wikisource", "wikinews", "wikibooks",
    "wikiquote", "wikivoyage", "wikiversity", "wikispecies",
}


def fetch_sitematrix() -> dict:
    """一次请求拿到所有语言 × 所有项目。缓存到 data/raw。"""
    if exists(OUT_RAW):
        log("  sitematrix 命中缓存")
        return read_json(OUT_RAW)
    log("  抓 sitematrix（1 次请求）")
    data = http_json(SITEMATRIX)
    write_json(OUT_RAW, data)
    return data


def main() -> None:
    banner("1. 维基媒体项目数（社群厚度）")
    sm = fetch_sitematrix()
    langs = [v for k, v in sm.get("sitematrix", {}).items() if str(k).isdigit()]
    by_wiki_code: dict[str, dict] = {}
    for entry in langs:
        code = entry.get("code")
        if not code:
            continue
        projects = sorted({
            s.get("code") for s in entry.get("site", [])
            if s.get("code") in CONTENT_PROJECTS
        })
        by_wiki_code[code] = {
            "projects": projects,
            "n": len(projects),
            # n_extra = 除维基百科以外还有几个项目
            "n_extra": len([p for p in projects if p != "wikipedia"]),
        }
    multi = [c for c, v in by_wiki_code.items() if v["n_extra"] >= 2]
    log(f"  语言版本 = {len(by_wiki_code)}")
    log(f"  有维基百科之外的 >=2 个项目 = {len(multi)} 个")
    top = sorted(by_wiki_code.items(), key=lambda kv: -kv[1]["n"])[:5]
    for c, v in top:
        log(f"    {c:<8} {v['n']:>2} 个项目: {', '.join(v['projects'])}")

    banner("2. Glottolog 描述深度（med）")
    # ⚠️ med 是**编码值**，不是篇数。码表（实测全量 9,317 门）：
    #     0 = long_grammar       长篇参考语法   1,970 门
    #     1 = grammar            语法          1,080 门
    #     2 = grammar_sketch     语法概述       2,113 门
    #     3 = phonology_or_text  音系或文本     1,520 门
    #     4 = wordlist_or_less   词表或更少     2,634 门
    # **刻度是反的：0 最好、4 最差。**
    # 我一开始按"文献篇数"理解，看到 English 的 med=0 才发现口径错了
    # （0 其实是"长篇参考语法"）。这里直接转成 depth = 5 - raw，
    # 越高越好，避免前端再把坐标轴画反一次。
    MED_LABEL = {
        0: ("med-long_grammar", "长篇参考语法", "long grammar"),
        1: ("med-grammar", "语法", "grammar"),
        2: ("med-grammar_sketch", "语法概述", "grammar sketch"),
        3: ("med-phonology_or_text", "音系或文本", "phonology or text"),
        4: ("med-wordlist_or_less", "词表或更少", "wordlist or less"),
    }
    by_glottocode: dict[str, dict] = {}
    if not exists(VALUES_CSV):
        log("  !! 没有 values.csv，跳过。先跑 06_fetch_aes.py")
    else:
        with open(VALUES_CSV, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("Parameter_ID") != "med":
                    continue
                raw = (row.get("Value") or "").strip()
                if raw not in {"0", "1", "2", "3", "4"}:
                    continue
                v = int(raw)
                code, zh, en = MED_LABEL[v]
                by_glottocode[row["Language_ID"]] = {
                    "raw": v,
                    "depth": 5 - v,          # 5 = 最好，1 = 最差
                    "code": code,
                    "label_zh": zh,
                    "label_en": en,
                }
        log(f"  有 med 的语言 = {len(by_glottocode):,}")
        if by_glottocode:
            dist = {}
            for d in by_glottocode.values():
                dist[d["depth"]] = dist.get(d["depth"], 0) + 1
            for depth in sorted(dist, reverse=True):
                zh = MED_LABEL[5 - depth][1]
                log(f"    depth={depth} ({zh}) {dist[depth]:>6,} 门")

    banner("3. 写入")
    write_json(OUT, {
        "by_wiki_code": by_wiki_code,
        "by_glottocode": by_glottocode,
        "meta": {
            "sitematrix_languages": len(by_wiki_code),
            "with_extra_projects": len(multi),
            "med_languages": len(by_glottocode),
            "med_scale": {
                "note": "Glottolog med 是编码值且刻度反向（0 最好）。已转成 depth = 5 - raw，越高越好。",
                "labels": {
                    "5": "长篇参考语法", "4": "语法", "3": "语法概述",
                    "2": "音系或文本", "1": "词表或更少",
                },
            },
            "content_projects": sorted(CONTENT_PROJECTS),
            "sources": {
                "projects": "https://meta.wikimedia.org/w/api.php?action=sitematrix",
                "med": "Glottolog CLDF values.csv (Parameter_ID=med)",
            },
        },
    })
    log(f"  {OUT}")


if __name__ == "__main__":
    main()
