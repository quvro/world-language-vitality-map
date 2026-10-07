# -*- coding: utf-8 -*-
import re, json, time
import urllib.request, urllib.error, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=45, headers=None):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

PHP = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.ihchina.cn/project.html"}

def summ(txt):
    try:
        j = json.loads(txt)
        n = len(j.get("list") or [])
        f = (j.get("list") or [{}])[0]
        return f"total={j.get('total')} p={j.get('p')} nrows={n} first_num={f.get('num')!r}"
    except Exception:
        return "NOT-JSON len=%d %r" % (len(txt), txt[:80])

print("### PROJECT endpoint: param spelling permutations ###")
variants = [
    "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=2",
    "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&page=2",
    "province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=2&page=2",
    "?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=50&p=1",
    "?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=20&p=3",
    "?category_id=16&limit=30&p=4",
    "?limit=30&p=4&category_id=16&province=&cate=&type=&rx_time=&keywords=",
]
for v in variants:
    url = "https://www.ihchina.cn/getProject.html" + (v if v.startswith("?") else "?" + v)
    st, hd, body = get(url, headers=PHP)
    print(f"  {url.split('getProject.html')[1]}\n     status={st} bytes={len(body)} {summ(body.decode('utf-8','replace'))}")
    time.sleep(0.5)

print("\n### PROJECT via category tid pages (project.html?tid=N) ###")
for tid in [1, 10]:
    st, hd, body = get(f"https://www.ihchina.cn/project.html?tid={tid}", headers={"User-Agent": UA})
    t = body.decode("utf-8", "replace")
    m = re.search(r'category_id\s*=\s*"(\d+)"', t)
    print(f"  tid={tid} status={st} bytes={len(body)} category_id_in_js={m.group(1) if m else None}")

print("\n### Does getProject work with tid's category_id? ###")
for cid in ["1", "10", "16", "2"]:
    st, hd, body = get(f"https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id={cid}&limit=10&p=1", headers=PHP)
    print(f"  category_id={cid} status={st} bytes={len(body)} {summ(body.decode('utf-8','replace'))}")
    time.sleep(0.4)

print("\n### NRCCA content inspection ###")
for u in ["http://www.nrcca.org.cn/", "http://test.nrcca.org.cn/representative.html"]:
    st, hd, body = get(u, timeout=40)
    t = body.decode("utf-8", "replace")
    print("=" * 65)
    print(f"{u} -> status={st} bytes={len(body)}")
    print("  <title>:", (re.search(r"<title>(.*?)</title>", t, re.S) or [None, "?"])[1].strip()[:120] if re.search(r"<title>", t) else "?")
    ajax = sorted(set(re.findall(r'\$\.(?:get|post|ajax)\s*\(\s*["\']([^"\']+)["\']', t)))
    print("  ajax endpoints:", ajax[:10])
    # look for tables / row counts
    rows = re.findall(r"<tr", t)
    print("  <tr> count:", len(rows))
    # find any 'project'/'representative' links
    links = sorted(set(re.findall(r'href="([^"]*(?:project|representative|ccr|detail)[^"]*)"', t, re.I)))
    print("  data-ish links:", links[:12])
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    print("  TEXT:", txt[:700])
