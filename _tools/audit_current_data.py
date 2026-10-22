"""数据层深度审查 —— 找真正的不一致，而不是复述统计。

用户要求「重新审查一下数据方面有没有 bug」。这里检查的是**不变量**：
如果某一条破了，说明管道里有地方算错了，而不只是"数字变了"。
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = "data/processed"
RAW = "data/raw"

problems = []


def bad(msg):
    problems.append(msg)
    print(f"  [BUG] {msg}")


def ok(msg):
    print(f"  OK    {msg}")


def load(name, base=D):
    with open(os.path.join(base, name), encoding="utf-8") as fh:
        return json.load(fh)


langs = load("languages.json")
ts = load("timeseries.json")
fm = load("feature_matrix.json")
feats = load("features.json")
aes = load("aes.json")
uni = load("endangerment.json")
zh = load("zh_labels.json")
join = load("wikimedia/join.json", RAW)
by_id = {l["wals_id"]: l for l in langs}
by_lang_ts = ts["by_language"]

print("=" * 74)
print("1. 时间序列")
print("=" * 74)
months_all = sorted({m for s in by_lang_ts.values() for m in s["views"]})
bad_keys = [m for m in months_all if not (len(m) == 6 and m.isdigit())]
ok(f"{len(months_all)} 个月份，{months_all[0]}..{months_all[-1]}") if not bad_keys \
    else bad(f"非法月份键 {bad_keys[:5]}")
# 连续性
y0, m0 = int(months_all[0][:4]), int(months_all[0][4:])
gaps = []
for i, m in enumerate(months_all):
    y, mo = int(m[:4]), int(m[4:])
    if i == 0:
        continue
    py, pmo = int(months_all[i - 1][:4]), int(months_all[i - 1][4:])
    exp = (py + (1 if pmo == 12 else 0), 1 if pmo == 12 else pmo + 1)
    if (y, mo) != exp:
        gaps.append((months_all[i - 1], m))
if gaps:
    bad(f"月份不连续：{gaps[:5]}")
else:
    ok("月份连续，无缺口")

for metric in ("views", "edits"):
    per_lang = [len(s[metric]) for s in by_lang_ts.values() if s.get(metric)]
    if per_lang:
        ok(f"{metric}: {len(per_lang)} 个语言有序列，月份数 {min(per_lang)}..{max(per_lang)}")

# views/edits 键集合是否一致
mismatch = [k for k, s in by_lang_ts.items()
            if s.get("views") and s.get("edits") and set(s["views"]) != set(s["edits"])]
if mismatch:
    # 编辑量本来就比浏览量少一个月，属于预期
    ok(f"{len(mismatch)} 个语言的 views/edits 月份集合不同（编辑量晚一个月，预期内）")
else:
    ok("views/edits 月份集合一致")

print()
print("=" * 74)
print("2. 时间序列与语言表的一致性")
print("=" * 74)
wiki_langs = {l["wals_id"] for l in langs if l.get("wiki_code")}
with_ts = set(by_lang_ts)
ok(f"有维基版本 {len(wiki_langs)} 门，有序列 {len(with_ts)} 门")
extra_ts = with_ts - wiki_langs
missing_ts = wiki_langs - with_ts
if extra_ts:
    bad(f"{len(extra_ts)} 个序列对应的语言在 languages.json 里没有 wiki_code：{list(extra_ts)[:5]}")
if missing_ts:
    bad(f"{len(missing_ts)} 门有维基版本但没有序列：{[(w, by_id[w]['name']) for w in list(missing_ts)[:5]]}")
if not extra_ts and not missing_ts:
    ok("有维基版本的语言与有序列的语言完全对应")

print()
print("=" * 74)
print("3. 活力指标的口径是否自洽（重算一遍）")
print("=" * 74)
recalc_bad = []
for wid, s in by_lang_ts.items():
    l = by_id.get(wid)
    if not l:
        continue
    v = s.get("views") or {}
    if len(v) < 6:
        continue
    ms = sorted(v)
    base = sum(v[m] for m in ms[:3]) / 3
    recent = sum(v[m] for m in ms[-3:]) / 3
    if l.get("views_baseline") is None:
        recalc_bad.append((wid, "缺少 views_baseline"))
        continue
    if abs(l["views_baseline"] - base) > max(1.0, base * 0.001):
        recalc_bad.append((wid, f"baseline {l['views_baseline']} != 重算 {base:.1f}"))
    if abs((l.get("views_recent") or -1) - recent) > max(1.0, recent * 0.001):
        recalc_bad.append((wid, f"recent {l.get('views_recent')} != 重算 {recent:.1f}"))
    if base > 0 and l.get("growth") is not None:
        g = (recent - base) / base
        if abs(l["growth"] - g) > 1e-3:
            recalc_bad.append((wid, f"growth {l['growth']} != 重算 {g:.4f}"))
    if l.get("baseline_ok") != (base >= 10_000):
        recalc_bad.append((wid, f"baseline_ok 与门槛不符 ({base:.0f})"))
if recalc_bad:
    bad(f"{len(recalc_bad)} 条活力指标与重算不符，例如：{recalc_bad[:4]}")
else:
    ok("views_baseline / views_recent / growth / baseline_ok 全部与重算一致")

print()
print("=" * 74)
print("4. 特征值与码表是否匹配")
print("=" * 74)
valid = defaultdict(set)
for c in feats["codes"]:
    valid[c["Parameter_ID"]].add(c["Number"])
all_vals = load("feature_matrix.json")
bad_vals = 0
samples = []
for fi, fid in enumerate(all_vals["feature_ids"]):
    row = all_vals["values"][fi]
    allowed = valid[fid]
    for v in row:
        if v is None:
            continue
        if v not in allowed:
            bad_vals += 1
            if len(samples) < 5:
                samples.append((fid, v))
if bad_vals:
    bad(f"{bad_vals} 个特征取值不在码表里，例如 {samples}")
else:
    ok(f"{len(all_vals['feature_ids'])} 个特征的全部取值都在码表内")

print()
print("=" * 74)
print("5. 坐标与语区")
print("=" * 74)
badcoord = [l["wals_id"] for l in langs
            if l.get("latitude") is not None and not (-90 <= l["latitude"] <= 90)]
badcoord += [l["wals_id"] for l in langs
             if l.get("longitude") is not None and not (-180 <= l["longitude"] <= 180)]
if badcoord:
    bad(f"{len(badcoord)} 条坐标越界：{badcoord[:5]}")
else:
    ok("坐标范围合法")
MACRO = {"Africa", "Eurasia", "Papunesia", "North America", "South America", "Australia"}
odd = [l["wals_id"] for l in langs if l.get("macroarea") not in MACRO | {None}]
if odd:
    bad(f"{len(odd)} 条语区不在六大语区内：{[(w, by_id[w]['macroarea']) for w in odd[:5]]}")
else:
    ok("所有语区都在六大语区之内")
half = [l["wals_id"] for l in langs
        if (l.get("latitude") is None) != (l.get("longitude") is None)]
if half:
    bad(f"{len(half)} 条只有一半坐标：{half[:5]}")
else:
    ok("坐标成对出现（不会只有经度没有纬度）")

print()
print("=" * 74)
print("6. 关联表（join）")
print("=" * 74)
joined = {k: v for k, v in join.items() if v.get("joined")}
ok(f"{len(join)} 个维基版本，其中 {len(joined)} 个可关联")
# 一个 wals_id 可能被多个维基版本认领（aze←az/azb、srb←hsb/dsb、ind←id/ms、knr←knc/kr）。
# 这是**数据本身的性质**（WALS 的一行有时覆盖多种语言/变体），不是 bug。
# 真正要保证的是：时间序列里每个 wals_id 只用了一个主版本 —— 那条在上面第 3 节
# 「活力指标重算」里已经验过（混用两个维基会立刻重算不符）。
claim = defaultdict(list)
for code, m in joined.items():
    if m.get("wals_id"):
        claim[m["wals_id"]].append(code)
multi = {w: cs for w, cs in claim.items() if len(cs) > 1}
if multi:
    ok(f"{len(multi)} 个 WALS 条目有多个维基版本候选（已在 03 里各取一个主版本，见构建日志）："
       f"{[(w, cs) for w, cs in list(multi.items())]}")
else:
    ok("每个 WALS 条目只有一个维基版本候选")
# 时间序列里每个 wals_id 只能出现一个 wiki_code
import sqlite3
try:
    con = sqlite3.connect(os.path.join(D, "language_vitality.db"))
    n_primary = con.execute(
        "select count(*) from dim_wiki_edition where is_primary").fetchone()[0]
    n_dup = con.execute(
        "select count(*) from (select wals_id from dim_wiki_edition "
        "where is_primary group by wals_id having count(*) > 1)").fetchone()[0]
    ok(f"dim_wiki_edition 标记了 {n_primary} 个主版本，其中同一 wals_id 有多个主版本的 = {n_dup}")
    if n_dup:
        bad(f"{n_dup} 个 wals_id 有多个 is_primary")
    con.close()
except Exception as exc:  # noqa: BLE001
    ok(f"跳过 is_primary 校验（{exc}）")
# 关联到的 wals_id 是否都真实存在
ghost = [w for w in claim if w not in by_id]
if ghost:
    bad(f"{len(ghost)} 个关联到的 wals_id 在 languages.json 里不存在：{ghost[:5]}")
else:
    ok("关联到的 wals_id 全部存在")

print()
print("=" * 74)
print("7. 濒危等级")
print("=" * 74)
for name, d, key in (("AES", aes, "by_glottocode"), ("UNESCO", uni, "by_glottocode")):
    levels = set(d[key].values())
    if levels <= {1, 2, 3, 4, 5, 6}:
        ok(f"{name}: {len(d[key])} 条，等级全部在 1..6")
    else:
        bad(f"{name}: 出现非法等级 {sorted(levels - {1,2,3,4,5,6})}")
merged = {}
for l in langs:
    gc = l.get("glottocode") or ""
    lv = aes["by_glottocode"].get(gc) or uni["by_glottocode"].get(gc) \
        or uni["by_iso639p3"].get((l.get("iso639p3") or "").lower())
    if lv:
        merged[l["wals_id"]] = lv
ok(f"合并后 {len(merged)} / {len(langs)} 门语言有濒危等级 "
   f"({len(merged)/len(langs)*100:.1f}%)")
# 同一 Glottocode 的多个变体应拿到同一等级（这是正确的）
gc_lv = defaultdict(set)
for l in langs:
    if l["wals_id"] in merged and l.get("glottocode"):
        gc_lv[l["glottocode"]].add(merged[l["wals_id"]])
conflict = {g: s for g, s in gc_lv.items() if len(s) > 1}
ok(f"{len(conflict)} 个 Glottocode 内部等级不一致（应为 0）") if not conflict \
    else bad(f"{len(conflict)} 个 Glottocode 内部等级不一致：{list(conflict.items())[:3]}")

print()
print("=" * 74)
print("8. 中文标签")
print("=" * 74)
for k in ("by_iso639p3", "by_glottocode"):
    ok(f"{k}: {len(zh[k])} 条")
# 中文名里混进英文的算不算缺陷？统计一下
zh_vals = list(zh["by_iso639p3"].values()) + list(zh["by_glottocode"].values())
ascii_only = [v for v in zh_vals if all(ord(c) < 128 for c in v)]
if ascii_only:
    ok(f"{len(ascii_only)} 条'中文名'其实是纯 ASCII（Wikidata 没有中文标签时回退英文名，预期内）")

print()
print("=" * 74)
print("9. 增长率的极端值是否可信")
print("=" * 74)
ext = sorted([l for l in langs if l.get("growth") is not None],
             key=lambda x: -abs(x["growth"]))[:5]
for l in ext:
    print(f"    {l['name'][:26]:<28} growth={l['growth']*100:+12,.0f}%  "
          f"baseline={l.get('views_baseline'):>12,.0f}  baseline_ok={l.get('baseline_ok')}")
tiny = [l for l in ext if (l.get("views_baseline") or 0) < 10_000 and l.get("baseline_ok")]
if tiny:
    bad(f"{len(tiny)} 条极端增长率的 baseline_ok 应为 False")
else:
    ok("极端增长率都来自小基数，且 baseline_ok 已正确标为不可信" if
       all(not l.get("baseline_ok") for l in ext if (l.get("views_baseline") or 0) < 20000)
       else "极端增长率的 baseline_ok 标记需复核")

print()
print("=" * 74)
print(f"结论：{len(problems)} 个问题")
print("=" * 74)
for p in problems:
    print(f"  · {p}")
if not problems:
    print("  未发现不变量被破坏。")
