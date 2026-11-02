"""08 · 四套口径的交叉验证：秩相关矩阵

动机
----
此前"四套口径同向"是**看着四根条都往上走**得出的结论，属于目测。
目测挡不住这个追问：「你怎么知道同向，不是你挑了四张看起来像的图？」

这里用 Spearman 秩相关把"同向"变成一个可检验的数。

为什么用 Spearman 而不是 Pearson
--------------------------------
· 四套梯度的量纲完全不同（特征数 0–192、深度 1–5、文献数 0–30、在场 0/1、等级 1–6）
· 分布严重偏斜（多数语言记录很少，少数很多），Pearson 会被极值主导
· 秩相关只问"排序是否一致"，正对应"被记录得越少，越可能在网上不存在"这句话

产出
----
data/processed/correlations.json
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = PROC / "correlations.json"


def jload(name: str):
    return json.load(io.open(PROC / name, encoding="utf-8"))


def _num(v):
    """把各种形状的取值归一成 float / None。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v) if not (isinstance(v, float) and np.isnan(v)) else None
    if isinstance(v, dict):
        for k in ("depth", "n_extra", "works", "level", "value", "n"):
            if k in v:
                return _num(v[k])
    return None


def main() -> None:
    print("载入数据 …")
    langs = jload("languages.json")
    langs = langs["languages"] if isinstance(langs, dict) else langs
    aes = jload("aes.json").get("by_glottocode", {})
    dp = jload("digital_presence.json")
    by_gc = dp.get("by_glottocode", {})
    lit = dp.get("literature", {})
    fm = jload("feature_matrix.json")

    keys = fm["language_keys"]
    vals = fm["values"]
    row_of = {k: i for i, k in enumerate(keys)}
    print(f"  语言 {len(langs)} 门；矩阵 {len(keys)} 行 × {len(fm['feature_ids'])} 特征")

    # ---- 每门语言取五个梯度的原始值 ----
    rec = []
    for lang in langs:
        gc = lang.get("glottocode")
        wid = lang.get("wals_id")

        # 1) WALS 记录完整度：矩阵行里非空特征数
        fc = None
        col = row_of.get(wid) if wid else None
        if col is not None:
            # values 是**特征优先**的：values[feature_idx][lang_idx]
            fc = sum(1 for f in range(len(vals))
                     if vals[f][col] is not None and vals[f][col] != "")

        # 2) 描写深度（1–5）；3) 描写文献数
        depth = _num(by_gc.get(gc)) if gc else None
        works = None
        if gc:
            works = _num(lit.get(gc))
            if works is None and isinstance(by_gc.get(gc), dict):
                works = _num(by_gc[gc].get("works"))

        # 4) 数字在场：是否有维基版本
        has_wiki = 1.0 if lang.get("wiki_code") else 0.0

        # 5) 濒危等级 1–6（越大越濒危）
        lvl = _num(aes.get(gc)) if gc else None

        rec.append(dict(fc=fc, depth=depth, works=works,
                        wiki=has_wiki, lvl=lvl, growth=lang.get("growth")))

    def pair(a: str, b: str):
        xs, ys = [], []
        for r in rec:
            if r[a] is None or r[b] is None:
                continue
            xs.append(r[a])
            ys.append(r[b])
        if len(xs) < 10 or len(set(xs)) < 2 or len(set(ys)) < 2:
            return None
        rho, p = spearmanr(xs, ys)
        return dict(rho=float(rho), p=float(p), n=len(xs))

    # 假设方向：前四对应当正相关，含濒危等级的两对应当负相关
    PAIRS = [
        ("fc", "depth", "WALS 记录完整度", "描写深度", +1),
        ("fc", "works", "WALS 记录完整度", "描写文献数", +1),
        ("depth", "works", "描写深度", "描写文献数", +1),
        ("fc", "wiki", "WALS 记录完整度", "有维基版本", +1),
        ("depth", "wiki", "描写深度", "有维基版本", +1),
        ("lvl", "wiki", "濒危等级", "有维基版本", -1),
        ("lvl", "fc", "濒危等级", "WALS 记录完整度", -1),
        ("lvl", "depth", "濒危等级", "描写深度", -1),
    ]

    out = []
    print("\n  ρ        p         n   方向  结论   变量对")
    print("  " + "-" * 74)
    for a, b, la, lb, sign in PAIRS:
        r = pair(a, b)
        if r is None:
            print(f"  (跳过) 样本不足：{la} × {lb}")
            continue
        ok = (r["rho"] > 0) == (sign > 0)
        sig = "***" if r["p"] < 1e-3 else "**" if r["p"] < 1e-2 else "*" if r["p"] < 0.05 else "n.s."
        verdict = "同向" if ok else "反向"
        print(f"  {r['rho']:+.3f}  {r['p']:.2e}  {r['n']:5d}  {sign:+d}   "
              f"{verdict:4s} {sig:4s} {la} × {lb}")
        out.append(dict(a=a, b=b, label_a=la, label_b=lb,
                        expected_sign=sign, **r,
                        same_direction=ok, significant=r["p"] < 0.05))

    n_ok = sum(1 for o in out if o["same_direction"] and o["significant"])
    print(f"\n  {len(out)} 对中 {n_ok} 对显著且与假设同向")

    res = dict(
        method="Spearman rank correlation",
        why="量纲不同、分布偏斜，秩相关只问排序是否一致",
        note="只在该对两个变量都有值的语言上计算",
        pairs=out,
        n_same_direction=n_ok,
        n_pairs=len(out),
    )
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(res, ensure_ascii=False, indent=2))
    print(f"  已写出 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
