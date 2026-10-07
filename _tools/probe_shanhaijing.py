# -*- coding: utf-8 -*-
"""Probe A v2: fetch the COMPLETE Shanhaijing text and measure extractable structure.

Wikisource organises the text as 山海經 (四庫全書本)/卷01..卷18 — v1 wrongly matched
only 4 pages by chapter name. Uses list=allpages with a prefix instead.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

# This host's console is GBK and the classical text contains CJK ext-B glyphs,
# so force UTF-8 on stdout and never let an encoding error kill the run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

API = "https://zh.wikisource.org/w/api.php"
UA = "CourseProjectFeasibilityProbe/1.0 (student research)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
os.makedirs(OUT, exist_ok=True)
OUT_FILE = os.path.join(OUT, "shanhaijing_probe.txt")

lines: list[str] = []


def log(text: str = "") -> None:
    lines.append(text)
    try:
        print(text[:160], flush=True)
    except Exception:  # noqa: BLE001
        pass


def api(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    params["formatversion"] = "2"
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def list_prefix(prefix: str) -> list[str]:
    out: list[str] = []
    cont: str | None = None
    while True:
        p = {"action": "query", "list": "allpages", "apprefix": prefix,
             "aplimit": 100}
        if cont:
            p["apcontinue"] = cont
        data = api(p)
        out += [x["title"] for x in data.get("query", {}).get("allpages", [])]
        cont = data.get("continue", {}).get("apcontinue")
        if not cont:
            break
        time.sleep(0.3)
    return out


PREFIX = "山海經 (四庫全書本)/"
log("=" * 78)
log(f"### 1. 列出版本页: {PREFIX}")
pages = list_prefix(PREFIX)
log(f"  共 {len(pages)} 页")
for t in pages:
    log(f"    * {t}")

if not pages:  # fall back to the annotated edition
    PREFIX = "山海經廣注 (四庫全書本)/"
    log(f"  回退到 {PREFIX}")
    pages = list_prefix(PREFIX)
    log(f"  共 {len(pages)} 页")

# --- 2. fetch ---------------------------------------------------------------
log("")
log("=" * 78)
log("### 2. 抓取正文")
texts: dict[str, str] = {}
for i in range(0, len(pages), 8):
    batch = pages[i:i + 8]
    try:
        data = api({"action": "query", "prop": "revisions", "rvprop": "content",
                    "rvslots": "main", "titles": "|".join(batch)})
    except Exception as exc:  # noqa: BLE001
        log(f"  batch failed: {exc}")
        continue
    for page in data.get("query", {}).get("pages", []):
        try:
            texts[page["title"]] = page["revisions"][0]["slots"]["main"]["content"]
        except (KeyError, IndexError):
            continue
    time.sleep(0.4)

full = "\n".join(texts.values())
log(f"  抓到 {len(texts)} 页, 原始 {len(full)} 字符")

clean = re.sub(r"\{\{[^}]*\}\}", "", full)
clean = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", clean)
clean = re.sub(r"'''?", "", clean)
clean = re.sub(r"<[^>]+>", "", clean)
# drop juan headers / metadata noise for measurement
log(f"  清洗后 {len(clean)} 字符")

log("")
log("=" * 78)
log("### 3. 可抽取结构测量")

GEO = re.findall(r"([\u4e00-\u9fff]{1,4}之山)", clean)
log(f"  「X之山」地理条目: {len(GEO)} 处, 去重 {len(set(GEO))}")

CREATURE = re.findall(r"有(獸|鳥|鱼|魚|蛇|蟲|虫|神|人)焉", clean)
log(f"  「有X焉」引入生物句式: {len(CREATURE)} 处 -> {Counter(CREATURE).most_common()}")

SHAPE = re.findall(r"其狀如([^，。]{1,10})", clean)
log(f"  「其狀如X」外形描述: {len(SHAPE)} 处, 去重 {len(set(SHAPE))}")
for s, n in Counter(SHAPE).most_common(15):
    log(f"    {s}: {n}")

NAMED = re.findall(r"(?:名|命)曰([\u4e00-\u9fff]{1,8})", clean)
log(f"  「名曰X」命名生物: {len(NAMED)} 处, 去重 {len(set(NAMED))}")
log("    样本: " + ", ".join(list(dict.fromkeys(NAMED))[:40]))

FEATURES = ["人面", "蛇身", "獸身", "鳥身", "龍身", "人身", "彘身", "羊身",
            "九尾", "四翼", "六足", "三足", "三首", "一目", "三目", "白首",
            "赤足", "虎齒", "牛尾", "彘鬣", "有翼", "無口", "善走", "食人",
            "見則", "其音如", "其鳴自", "可以已", "佩之", "食之", "能言",
            "如嬰兒", "戴角", "被毛", "五采", "文身"]
feat_counts = Counter({f: clean.count(f) for f in FEATURES if clean.count(f)})
log(f"  特征词命中: {len(feat_counts)}/{len(FEATURES)}")
for f, n in feat_counts.most_common(50):
    log(f"    {f}: {n}")

OMEN = re.findall(r"見則([^。，]{2,24})", clean)
log(f"  「見則…」预兆句式: {len(OMEN)} 处; 样本: "
    + " / ".join(list(dict.fromkeys(OMEN))[:12]))

MED = re.findall(r"可以(?:已|治)([^，。]{1,14})", clean)
log(f"  「可以已X」药用句式: {len(MED)} 处; 样本: "
    + ", ".join(list(dict.fromkeys(MED))[:15]))

SACRIFICE = re.findall(r"其祠[之禮]?([^。]{2,40})", clean)
log(f"  「其祠…」祭祀句式: {len(SACRIFICE)} 处")

GODS = re.findall(r"([\u4e00-\u9fff]{1,6}神)", clean)
log(f"  「X神」提及: {len(GODS)} 处, 去重 {len(set(GODS))}; "
    + ", ".join(f"{g}({n})" for g, n in Counter(GODS).most_common(15)))

log("")
log("=" * 78)
log("### 4. 小结（决定 A 能否撑起交互）")
log(f"  正文字符数         : {len(clean)}")
log(f"  地理条目 X之山(去重): {len(set(GEO))}")
log(f"  生物引入 有X焉      : {len(CREATURE)}")
log(f"  命名生物 名曰X(去重) : {len(set(NAMED))}")
log(f"  外形描述 其狀如X(去重): {len(set(SHAPE))}")
log(f"  可用特征维度        : {len(feat_counts)}")
log(f"  预兆句式            : {len(OMEN)}")
log(f"  药用句式            : {len(MED)}")

with open(OUT_FILE, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print(f"wrote {OUT_FILE}")
