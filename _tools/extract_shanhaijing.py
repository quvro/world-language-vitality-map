# -*- coding: utf-8 -*-
"""Probe A v3: prototype the ACTUAL extraction pipeline.

If the Shanhaijing text can be split into one structured record per mountain
(name / direction / distance / produce / creature / appearance / features /
effect / omen), then project A is buildable. This measures that directly.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

API = "https://zh.wikisource.org/w/api.php"
UA = "CourseProjectFeasibilityProbe/1.0 (student research)"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_refs_out")
os.makedirs(OUT, exist_ok=True)
OUT_TXT = os.path.join(OUT, "shanhaijing_extract.txt")
OUT_JSON = os.path.join(OUT, "shanhaijing_sample.json")

lines: list[str] = []


def log(text: str = "") -> None:
    lines.append(text)
    try:
        print(text[:200], flush=True)
    except Exception:  # noqa: BLE001
        pass


def api(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    params["formatversion"] = "2"
    req = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


# --- fetch ------------------------------------------------------------------
data = api({"action": "query", "prop": "revisions", "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(f"山海經 (四庫全書本)/卷{i:02d}" for i in range(1, 19))})
raw = "\n".join(
    p["revisions"][0]["slots"]["main"]["content"]
    for p in data["query"]["pages"]
    if p.get("revisions")
)
text = re.sub(r"\{\{[^}]*\}\}", "", raw)
text = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", text)
text = re.sub(r"'''?", "", text)
text = re.sub(r"<[^>]+>", "", text)
text = re.sub(r"[\s]+", "", text)
log(f"正文字符数: {len(text)}")

# --- split into mountain records -------------------------------------------
MOUNT = re.compile(
    r"(又[東西南北上下]{0,4}|[東西南北]{1,2})?([\d一二三四五六七八九十百千]{1,8})里"
    r"[，,]?曰([\u4e00-\u9fff]{1,6}?)之山"
)
hits = list(MOUNT.finditer(text))
log(f"匹配到「…里，曰X之山」条目: {len(hits)}")

records: list[dict] = []
for i, m in enumerate(hits):
    start = m.end()
    end = hits[i + 1].start() if i + 1 < len(hits) else min(start + 400, len(text))
    block = text[start:end]
    rec: dict = {
        "山名": m.group(3) + "之山",
        "方位": (m.group(1) or "").strip(),
        "距离": m.group(2) + "里",
        "原文": block[:220],
    }
    yin = re.search(r"其陽多([^，。其]{1,12})", block)
    yang = re.search(r"其陰多([^，。其]{1,12})", block)
    up = re.search(r"其上多([^，。其]{1,12})", block)
    down = re.search(r"其下多([^，。其]{1,12})", block)
    rec["阳坡物产"] = yin.group(1) if yin else None
    rec["阴坡物产"] = yang.group(1) if yang else None
    rec["山上"] = up.group(1) if up else None
    rec["山下"] = down.group(1) if down else None

    kind = re.search(r"有(獸|鳥|魚|蛇|蟲|神|人)焉", block)
    rec["生物类别"] = kind.group(1) if kind else None
    shape = re.search(r"其狀如([^，。]{1,14})", block)
    rec["外形"] = shape.group(1) if shape else None
    name = re.search(r"其?名曰([\u4e00-\u9fff]{1,6})", block)
    rec["生物名"] = name.group(1) if name else None
    effect = re.search(r"(食之|佩之|服之|可以已)([^，。]{0,10})", block)
    rec["功效"] = (effect.group(1) + (effect.group(2) or "")) if effect else None
    omen = re.search(r"見則([^，。]{2,20})", block)
    rec["预兆"] = omen.group(1) if omen else None
    water = re.search(r"([\u4e00-\u9fff]{1,4}水)出于焉|([\u4e00-\u9fff]{1,4}水)出焉", block)
    rec["水系"] = (water.group(1) or water.group(2)) if water else None

    FEATS = ["人面", "蛇身", "獸身", "鳥身", "龍身", "人身", "彘身", "羊身",
             "九尾", "四翼", "六足", "三足", "三首", "一目", "三目", "白首",
             "赤足", "虎齒", "牛尾", "彘鬣", "有翼", "無口", "善走", "食人",
             "能言", "如嬰兒", "戴角", "被毛", "五采", "文身", "白耳", "四耳"]
    rec["特征"] = [f for f in FEATS if f in block] or None
    records.append(rec)

# --- quality report ---------------------------------------------------------
log("")
log("=" * 78)
log("### 抽取质量")
n = len(records)
fields = ["方位", "距离", "阳坡物产", "阴坡物产", "山上", "山下", "生物类别",
          "外形", "生物名", "功效", "预兆", "水系", "特征"]
log(f"  记录数: {n}")
for f in fields:
    filled = sum(1 for r in records if r.get(f))
    log(f"    {f:<8}: {filled:>4} / {n}  ({filled * 100 // max(n,1)}%)")

# creature-bearing records only
creatures = [r for r in records if r["生物类别"]]
log(f"  含生物的记录: {len(creatures)}")
log(f"    其中有名字: {sum(1 for r in creatures if r['生物名'])}")
log(f"    其中有外形: {sum(1 for r in creatures if r['外形'])}")
log(f"    其中有特征: {sum(1 for r in creatures if r['特征'])}")
log(f"    其中有功效: {sum(1 for r in creatures if r['功效'])}")
log(f"    其中有预兆: {sum(1 for r in creatures if r['预兆'])}")

with_feats = [r for r in creatures if r["特征"]]
log(f"  特征可用于共现网络的记录: {len(with_feats)}")
log("")
log("### 5 条完整样本记录")
for r in [x for x in creatures if x["生物名"] and x["特征"]][:5]:
    log(json.dumps(r, ensure_ascii=False, indent=2))
log("")
log("### 3 条预兆样本")
for r in [x for x in records if x["预兆"]][:3]:
    log(f"  {r['山名']}: 見則{r['预兆']}")

with open(OUT_JSON, "w", encoding="utf-8") as fh:
    json.dump(records, fh, ensure_ascii=False, indent=1)
with open(OUT_TXT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log(f"\nwrote {OUT_TXT} and {OUT_JSON}")
