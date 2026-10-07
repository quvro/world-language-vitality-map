# -*- coding: utf-8 -*-
"""Independently verify the ihchina datasets the audit claims to have pulled."""
import json
import os
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

D = os.path.dirname(os.path.abspath(__file__))
lines: list[str] = []


def log(t: str = "") -> None:
    lines.append(t)
    try:
        print(t[:220], flush=True)
    except Exception:  # noqa: BLE001
        pass


def load(name: str):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        log(f"!! missing: {name}")
        return None
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def inspect(name: str, keys_of_interest: list[str]) -> None:
    log("=" * 78)
    log(f"### {name}   ({os.path.getsize(os.path.join(D, name)) / 1e6:.1f} MB)")
    data = load(name)
    if data is None:
        return
    # find the row list whatever the envelope is
    rows = None
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for k in ("list", "data", "rows", "result", "results"):
            v = data.get(k)
            if isinstance(v, list) and v:
                rows = v
                log(f"  行数组位于 key='{k}'; 顶层其它 key: "
                    f"{[k2 for k2 in data.keys() if k2 != k]}")
                break
        if rows is None:
            rows = []
            for v in data.values():
                if isinstance(v, list) and len(v) > len(rows):
                    rows = v
    if not rows:
        log("  !! 未找到行数组")
        log(f"  顶层结构: {type(data).__name__}, keys="
            f"{list(data.keys())[:15] if isinstance(data, dict) else 'n/a'}")
        return
    log(f"  行数: {len(rows)}")
    log(f"  首行字段: {sorted(rows[0].keys())}")
    log("  字段覆盖:")
    for k in keys_of_interest:
        n = sum(1 for r in rows if r.get(k) not in (None, "", []))
        log(f"    {k:<16}: {n:>5} / {len(rows)}  ({n * 100 // len(rows)}%)")
    log("  样本 2 条:")
    for r in rows[:2]:
        log("    " + json.dumps(
            {k: (str(v)[:70] if v is not None else None) for k, v in r.items()},
            ensure_ascii=False,
        )[:600])


inspect("project_full.json",
        ["num", "title", "type", "cate", "rx_time", "province", "protect_unit", "id"])
inspect("representative_full.json",
        ["title", "sex", "nation", "type", "project", "province", "rx_time", "day"])

# extra: category / batch distributions for the projects file
log("")
log("=" * 78)
log("### 项目类别与批次分布（核对完整性）")
p = load("project_full.json")
if isinstance(p, dict):
    for k, v in p.items():
        if isinstance(v, list) and v:
            p = v
            break
if isinstance(p, list) and p:
    log("  类别分布:")
    for k, n in Counter(r.get("type") for r in p).most_common():
        log(f"    {k}: {n}")
    log("  批次分布:")
    for k, n in Counter(r.get("rx_time") for r in p).most_common():
        log(f"    {k}: {n}")
    log(f"  unique num(编号): {len({r.get('num') for r in p})}")
    log(f"  unique title: {len({r.get('title') for r in p})}")
    log(f"  unique id: {len({r.get('id') for r in p})}")

with open(os.path.join(D, "results_verify.json.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
log("\ndone")
