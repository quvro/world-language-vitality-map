# -*- coding: utf-8 -*-
import re, json, time, ssl
import urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=60, headers=None, data=None, ctx=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

def probe(url, label=""):
    st, hd, body = get(url, headers={"X-Requested-With": "XMLHttpRequest",
                                     "Referer": "https://www.ihchina.cn/project.html"})
    txt = body.decode("utf-8", "replace")
    info = f"status={st} bytes={len(body)}"
    try:
        j = json.loads(txt)
        n = len(j.get("list") or [])
        first = (j.get("list") or [{}])[0]
        info += f" | total={j.get('total')} count={j.get('count')} p={j.get('p')} nrows={n} first_num={first.get('num')!r} first_title={(first.get('title') or '')[:14]!r}"
    except Exception:
        info += " | not-json: " + txt[:100].replace("\n", " ")
    print(f"  [{label}] {url}\n      -> {info}")
    return txt

print("### 1. PROJECT endpoint: does p/limit work? (with cache buster) ###")
ts = int(time.time())
for q in ["province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=1",
          "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=2",
          "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=5",
          "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=1000&p=1",
          "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1",
          "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=5000&p=1",
          ]:
    probe(f"https://www.ihchina.cn/getProject.html?{q}&_={ts}", label="GET")
    time.sleep(0.4)

print("\n### 1b. POST form-encoded ###")
d = urllib.parse.urlencode({"province": "", "rx_time": "", "type": "", "cate": "",
                            "keywords": "", "category_id": "16", "limit": "100000", "p": "1"}).encode()
st, hd, body = get("https://www.ihchina.cn/getProject.html", data=d,
                   headers={"X-Requested-With": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded"})
txt = body.decode("utf-8", "replace")
try:
    j = json.loads(txt)
    print(f"  POST status={st} total={j.get('total')} nrows={len(j.get('list') or [])}")
except Exception:
    print(f"  POST status={st} not-json {txt[:150]}")

print("\n### 2. REPRESENTATIVE: pagination sanity (limit=10, p=2) ###")
probe("https://www.ihchina.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=10&p=2&_=%d" % ts, label="rep")

print("\n### 3. Representative row FIELD NAMES (full) ###")
st, hd, body = get("https://www.ihchina.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=3&p=1")
j = json.loads(body.decode("utf-8", "replace"))
row = j["list"][0]
print("  fields:", list(row.keys()))
print("  sample:", json.dumps({k: (str(v)[:60]) for k, v in row.items()}, ensure_ascii=False, indent=1)[:2500])

print("\n### 4. Project row FIELD NAMES (full) ###")
st, hd, body = get("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=1&_=%d" % (ts+1))
j = json.loads(body.decode("utf-8", "replace"))
row = j["list"][0]
print("  fields:", list(row.keys()))
print("  sample:", json.dumps({k: (str(v)[:60]) for k, v in row.items()}, ensure_ascii=False, indent=1)[:2500])

print("\n### 5. NRCCA / test.nrcca + detail page + sitemap ###")
for u in ["https://www.nrcca.org.cn/", "https://nrcca.org.cn/", "http://www.nrcca.org.cn/",
          "http://test.nrcca.org.cn/representative.html", "https://www.ihchina.cn/sitemap.html"]:
    st, hd, body = get(u, timeout=30)
    print(f"  {u} -> status={st} bytes={len(body)} ctype={hd.get('Content-Type')}")
    if st is None:
        print("     err:", body.decode("utf-8", "replace")[:200])

print("\n### 6. detail pages (do they 200?) ###")
for u in ["https://www.ihchina.cn/project_details/12178.html", "https://www.ihchina.cn/ccr_detail/716.html"]:
    st, hd, body = get(u, timeout=30)
    print(f"  {u} -> status={st} bytes={len(body)}")
