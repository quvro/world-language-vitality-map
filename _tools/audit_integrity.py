# -*- coding: utf-8 -*-
import re, json, io, time, collections
import urllib.request, urllib.error

OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=45, headers=None):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

print("### User's literal URLs (http, no .html) ###")
for u in ["http://www.ihchina.cn/project", "http://www.ihchina.cn/representative.html",
          "http://www.ihchina.cn/project.html", "https://www.ihchina.cn/project",
          "http://www.nrcca.org.cn/robots.txt", "http://www.ihchina.cn/robots.txt"]:
    st, hd, b = get(u, timeout=30)
    P(f"  {u} -> status={st} bytes={len(b)} ct={hd.get('Content-Type')} loc={hd.get('Location')}")
    if st == 200 and b"robots" in u.encode():
        P("     BODY:", b.decode("utf-8", "replace")[:300].replace("\n", " | "))

print("\n### nrcca mirrors: do they serve the SAME data? ###")
H = {"X-Requested-With": "XMLHttpRequest", "Referer": "http://test.nrcca.org.cn/representative.html"}
for u in ["http://test.nrcca.org.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=100000&p=1",
          "http://www.nrcca.org.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=100000&p=1",
          "http://test.nrcca.org.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1"]:
    st, hd, b = get(u, timeout=120, headers=H)
    try:
        j = json.loads(b.decode("utf-8", "replace"))
        P(f"  {u}\n     -> status={st} bytes={len(b)} total={j.get('total')} nrows={len(j.get('list') or [])}")
    except Exception:
        P(f"  {u}\n     -> status={st} bytes={len(b)} non-json {b[:100]!r}")

print("\n### project_full.json: category distribution + integrity ###")
with open(r"E:\develop\myprogram\keshihua\_tools\project_full.json", encoding="utf-8") as f:
    rows = json.load(f)
P(f"  total rows: {len(rows)}")
P(f"  unique id: {len(set(r['id'] for r in rows))}")
P(f"  unique project_num: {len(set(r['project_num'] for r in rows))}")
P(f"  unique num (项目编号): {len(set(r['num'] for r in rows))}")
P(f"  unique title: {len(set(r['title'] for r in rows))}")
P("  by 类别(type):")
for k, c in collections.Counter(r.get("type") for r in rows).most_common():
    P(f"    {k}: {c}")
P("  by 类型(cate):")
for k, c in collections.Counter(r.get("cate") for r in rows).most_common():
    P(f"    {k}: {c}")
P("  by 公布时间(rx_time):")
for k, c in collections.Counter(re.sub(r"</br>", " ", r.get("rx_time") or "") for r in rows).most_common():
    P(f"    {k!r}: {c}")
P(f"  unique 申报地区或单位(province): {len(set(r['province'] for r in rows))}")
P("  sample protected units:", [r.get("protect_unit") for r in rows[:3]])

print("\n### representative_full.json: national totals ###")
with open(r"E:\develop\myprogram\keshihua\_tools\representative_full.json", encoding="utf-8") as f:
    reps = json.load(f)
P(f"  total rows: {len(reps)}  unique id: {len(set(r['id'] for r in reps))}")
P("  by 性别(sex):")
for k, c in collections.Counter(r.get("sex") for r in reps).most_common():
    P(f"    {k!r}: {c}")
P("  by 民族(nation) top10:")
for k, c in collections.Counter(r.get("nation") for r in reps).most_common(10):
    P(f"    {k!r}: {c}")
P("  by 批次(rx_time) top10:")
for k, c in collections.Counter(r.get("rx_time") for r in reps).most_common(10):
    P(f"    {k!r}: {c}")
P("  day (出生年月) coverage: %d/%d" % (sum(1 for r in reps if r.get("day")), len(reps)))
P("  day samples:", [r.get("day") for r in reps if r.get("day")][:8])
P("  deaths mentioned in content:", sum(1 for r in reps if "去世" in (r.get("content") or "")))

with open(r"E:\develop\myprogram\keshihua\_tools\results_integrity.txt", "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
print("\n[saved]")
