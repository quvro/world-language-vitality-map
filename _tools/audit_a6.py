# -*- coding: utf-8 -*-
import re, json, time, random
import urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=45, headers=None, method="GET"):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

def summ(body):
    t = body.decode("utf-8", "replace")
    try:
        j = json.loads(t)
        f = (j.get("list") or [{}])[0]
        return f"JSON total={j.get('total')} p={j.get('p')} nrows={len(j.get('list') or [])} first={f.get('num')!r} title={(f.get('title') or '')[:10]!r}"
    except Exception:
        return f"NON-JSON({len(t)}B) {t[:60]!r}"

PROJ = "https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=PAGE"

print("### A. /getProject (no .html) - does it honor params? ###")
for q in ["", "?limit=100000&p=1", "?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=2"]:
    st, hd, b = get("https://www.ihchina.cn/getProject" + q, headers={"X-Requested-With": "XMLHttpRequest"})
    print(f"  /getProject{q[:60]} -> {st} {len(b)}B X-Cache={hd.get('X-Cache')} Age={hd.get('Age')} {summ(b)}")
    if q == "":
        print("   BODY:", b.decode("utf-8", "replace")[:1500])
    time.sleep(0.3)

print("\n### B. CDN cache-bypass attempts on getProject.html ###")
tries = [
    ("baseline p=2", PROJ.replace("PAGE", "2"), {}),
    ("Cache-Control: no-cache", PROJ.replace("PAGE", "2"), {"Cache-Control": "no-cache", "Pragma": "no-cache"}),
    ("Cookie set", PROJ.replace("PAGE", "2"), {"Cookie": "PHPSESSID=" + "".join(random.choices("abcdef0123456789", k=26))}),
    ("Accept-Encoding identity", PROJ.replace("PAGE", "2"), {"Accept-Encoding": "identity"}),
    ("HEAD-ish POST", PROJ.replace("PAGE", "2"), {"Content-Type": "application/x-www-form-urlencoded"}),
]
for label, url, hh in tries:
    h = {"X-Requested-With": "XMLHttpRequest"}
    h.update(hh)
    st, hd, b = get(url, headers=h)
    print(f"  [{label}] {st} {len(b)}B X-Cache={hd.get('X-Cache')} Age={hd.get('Age')} {summ(b)}")
    time.sleep(0.3)

print("\n### C. HTTP (not HTTPS) + alternate host paths ###")
alt = [
    "http://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=3",
    "https://www.ihchina.cn/getProject.html/?province=&category_id=16&limit=10&p=3",
    "https://www.ihchina.cn/getproject.html?limit=10&p=3",
    "https://www.ihchina.cn//getProject.html?limit=10&p=3",
]
for u in alt:
    st, hd, b = get(u, timeout=25, headers={"X-Requested-With": "XMLHttpRequest"})
    print(f"  {u[:95]}\n     -> {st} {len(b)}B ct={hd.get('Content-Type')} X-Cache={hd.get('X-Cache')} {summ(b) if b else ''}")
    time.sleep(0.3)

print("\n### D. Detail-page ID enumeration feasibility ###")
for u in ["https://www.ihchina.cn/project_details/1.html",
          "https://www.ihchina.cn/project_details/14000.html",
          "https://www.ihchina.cn/project_details/20000.html",
          "https://www.ihchina.cn/ccr_detail/1.html",
          "https://www.ihchina.cn/ccr_detail/9000.html"]:
    st, hd, b = get(u, timeout=25)
    has = "\u9879\u76ee\u7f16\u53f7".encode("utf-8") in b
    print(f"  {u} -> {st} {len(b)}B has_field_marker={has}")

print("\n### E. representative full pull + save ###")
st, hd, b = get("https://www.ihchina.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=100000&p=1",
                headers={"X-Requested-With": "XMLHttpRequest"})
print(f"  -> {st} {len(b)}B X-Cache={hd.get('X-Cache')}")
j = json.loads(b.decode("utf-8", "replace"))
rows = j["list"]
print(f"  rows={len(rows)}")
with open(r"E:\develop\myprogram\keshihua\_tools\representative_full.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
print("  saved representative_full.json")
# field coverage
keys = {}
for r in rows:
    for k, v in r.items():
        if v not in ("", None, "N;", "None"):
            keys[k] = keys.get(k, 0) + 1
print("  NON-EMPTY FIELD COVERAGE (of %d rows):" % len(rows))
for k, c in sorted(keys.items(), key=lambda x: -x[1]):
    print(f"    {k}: {c}")
