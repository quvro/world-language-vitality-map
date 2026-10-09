"""
M4 特征矩阵视图的可行性探查。

要回答三个问题，否则这个视图建出来可能只是装饰：
  1. 矩阵有多稀疏？空白是怎么分布的？
  2. 「记录得少」和「数字世界不可见」是不是相关的（双重缺席）？
  3. 特征之间是否存在强蕴含关系（能不能做一个共现/蕴含视图）？
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = "data/processed"


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return json.load(fh)


langs = load("languages.json")
matrix = load("feature_matrix.json")
features = load("features.json")

keys = matrix["language_keys"]
fids = matrix["feature_ids"]
vals = matrix["values"]
nl, nf = len(keys), len(fids)
total = nl * nf
filled = sum(1 for row in vals for v in row if v is not None)
print(f"矩阵规模 = {nl} 语言 × {nf} 特征 = {total:,} 格")
print(f"有值 = {filled:,} ({filled / total * 100:.1f}%)   空白 = {total - filled:,} "
      f"({(total - filled) / total * 100:.1f}%)")

# ---------------------------------------------------------------- 覆盖率分布
per_feature = [(fids[i], sum(1 for v in vals[i] if v is not None)) for i in range(nf)]
per_feature.sort(key=lambda x: -x[1])
name_of = {f["ID"]: f["Name"] for f in features["features"]}

print("\n=== 特征覆盖率：记录得最全 / 最差的 ===")
print("  最全的 5 个:")
for fid, c in per_feature[:5]:
    print(f"    {fid:<6} {c:>5} 语言 ({c / nl * 100:5.1f}%)  {name_of.get(fid, '')[:40]}")
print("  最差的 5 个:")
for fid, c in per_feature[-5:]:
    print(f"    {fid:<6} {c:>5} 语言 ({c / nl * 100:5.1f}%)  {name_of.get(fid, '')[:40]}")
covs = [c for _, c in per_feature]
print(f"  中位数 = {sorted(covs)[len(covs) // 2]} 语言 ({sorted(covs)[len(covs)//2]/nl*100:.1f}%)")
print(f"  覆盖率 > 50% 的特征 = {sum(1 for c in covs if c > nl * 0.5)} 个")
print(f"  覆盖率 < 20% 的特征 = {sum(1 for c in covs if c < nl * 0.2)} 个")

# ---------------------------------------------------------------- 每语言覆盖
per_lang = {}
for i, k in enumerate(keys):
    per_lang[k] = sum(1 for row in vals if row[i] is not None)
by_id = {l["wals_id"]: l for l in langs}
lcov = sorted(per_lang.items(), key=lambda x: -x[1])
print("\n=== 语言的数据完整度 ===")
for k, c in lcov[:3]:
    print(f"    最全 {by_id.get(k, {}).get('name', k):<28} {c:>4} 个特征")
for k, c in lcov[-3:]:
    print(f"    最少 {by_id.get(k, {}).get('name', k):<28} {c:>4} 个特征")
med = sorted(per_lang.values())[len(per_lang) // 2]
print(f"  中位数 = {med} 个特征")

# ------------------------------------------------------- 双重缺席：记录 vs 数字
print("\n=== 「记录得少」与「数字不可见」是否相关 ===")
buckets = defaultdict(lambda: {"n": 0, "wiki": 0})
for k, c in per_lang.items():
    b = "<30" if c < 30 else "30-79" if c < 80 else "80-149" if c < 150 else ">=150"
    buckets[b]["n"] += 1
    if by_id.get(k, {}).get("wiki_code"):
        buckets[b]["wiki"] += 1
for b in ["<30", "30-79", "80-149", ">=150"]:
    d = buckets[b]
    if d["n"]:
        print(f"  WALS 收录 {b:>6} 个特征的语言: {d['n']:>5} 门, "
              f"其中有维基版本 {d['wiki']:>4} 门 ({d['wiki'] / d['n'] * 100:5.1f}%)")

# 相关系数（点二列）
xs = [per_lang[k] for k in keys]
ys = [1 if by_id.get(k, {}).get("wiki_code") else 0 for k in keys]
mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
print(f"  点二列相关 r = {num / den:.3f}（正=记录越全越可能有维基版本）")

# ---------------------------------------------------------------- 特征蕴含关系
print("\n=== 特征之间的强蕴含关系（条件概率）===")
# 只用覆盖率较高的特征，否则样本太小没有意义
top = [fid for fid, c in per_feature if c >= nl * 0.35][:40]
idx = {fid: fids.index(fid) for fid in top}
print(f"  参与分析的特征 = {len(top)} 个（覆盖率 >= 35%）")

pairs = []
for a in top:
    ra = vals[idx[a]]
    for b in top:
        if a >= b:
            continue
        rb = vals[idx[b]]
        # P(b有值 | a有值) 与 P(b有值 | a无值) 的差 —— 差越大说明越有蕴含性
        both = only_a = only_b = neither = 0
        for i in range(nl):
            va, vb = ra[i] is not None, rb[i] is not None
            if va and vb:
                both += 1
            elif va:
                only_a += 1
            elif vb:
                only_b += 1
            else:
                neither += 1
        if both + only_a < 20 or both + only_b < 20:
            continue
        p_b_given_a = both / (both + only_a)
        p_b_given_not_a = only_b / (only_b + neither) if (only_b + neither) else 0
        # 用 a 预测 b 的"补全能力"
        lift = p_b_given_a - p_b_given_not_a
        if abs(lift) > 0.8:
            pairs.append((abs(lift), lift, a, b, both, only_a))
pairs.sort(reverse=True)
print(f"  |条件概率差| > 0.8 的特征对 = {len(pairs)} 对，最强的 8 对:")
for _, lift, a, b, both, only_a in pairs[:8]:
    print(f"    {a:<6}{name_of.get(a, '')[:26]:<28} -> {b:<6}{name_of.get(b, '')[:26]:<28} "
          f"差 {lift:+.2f} (n={both + only_a})")
