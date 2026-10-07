# -*- coding: utf-8 -*-
import re, json
import urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=40, headers=None, data=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h, data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

def jget(url):
    st, hd, body = get(url, headers={"X-Requested-With": "XMLHttpRequest",
                                     "Referer": "https://www.ihchina.cn/project.html"})
    print("=" * 72)
    print(f"GET {url}")
    print(f"  status={st} bytes={len(body)} ctype={hd.get('Content-Type')}")
    txt = body.decode("utf-8", "replace")
    try:
        j = json.loads(txt)
        print("  JSON keys:", list(j.keys()))
        for k, v in j.items():
            if isinstance(v, list):
                print(f"    {k}: list[{len(v)}]")
            elif isinstance(v, (str, int, float, type(None))):
                s = str(v)
                print(f"    {k}: {s[:200]}")
            else:
                print(f"    {k}: {type(v)}")
        if isinstance(j.get("list"), list) and j["list"]:
            print("  FIRST ROW:", json.dumps(j["list"][0], ensure_ascii=False)[:900])
        return j
    except Exception as e:
        print("  not JSON:", e)
        print("  head:", txt[:600])
        return None

print("########## PROJECT ENDPOINT ##########")
pj = jget("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=1")
pj2 = jget("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=2")
pj3 = jget("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=1000&p=1")
pj4 = jget("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1")

print("\n########## REPRESENTATIVE ENDPOINT ##########")
for u in ["https://www.ihchina.cn/art/representative.html?province=&rx_time=&cate=&sex=&keywords=&limit=10&p=1",
          "https://www.ihchina.cn/art/representative.html?province=&rx_time=&cate=&sex=&keywords=&limit=100000&p=1"]:
    jget(u)

print("\n########## PAGE SCRIPTS (representative params) ##########")
st, hd, body = get("https://www.ihchina.cn/representative.html")
txt = body.decode("utf-8", "replace")
for m in re.finditer(r'<script[^>]*>(.*?)</script>', txt, re.S | re.I):
    s = m.group(1)
    if "representative.html" in s or "load_data" in s:
        print("---- block %d chars ----" % len(s))
        print(s[:5000])
        break

print("\n########## robots.txt ##########")
for u in ["https://www.ihchina.cn/robots.txt", "https://www.nrcca.org.cn/robots.txt"]:
    st, hd, body = get(u)
    print(f"{u} -> status={st} bytes={len(body)}")
    print(body.decode("utf-8", "replace")[:800])
