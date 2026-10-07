# -*- coding: utf-8 -*-
import re, json, time
import urllib.request, urllib.error

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

HDRS = ["Content-Type", "Content-Length", "Last-Modified", "ETag", "Cache-Control",
        "Expires", "Age", "X-Cache", "Via", "Server", "Set-Cookie", "Vary", "X-Powered-By"]

def dump(url, label):
    st, hd, body = get(url, headers={"X-Requested-With": "XMLHttpRequest",
                                     "Referer": "https://www.ihchina.cn/project.html"})
    print(f"--- {label}")
    print(f"    {url}")
    print(f"    status={st} bytes={len(body)}")
    for k in HDRS:
        if k in hd:
            print(f"      {k}: {hd[k]}")
    return st, hd, body

print("### HEADER FORENSICS: static file vs dynamic ###")
dump("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=1", "getProject limit10 p1")
dump("https://www.ihchina.cn/getProject.html?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=10&p=99", "getProject limit10 p99")
dump("https://www.ihchina.cn/getProject.html", "getProject NO params")
dump("https://www.ihchina.cn/getProject.html?keywords=%E6%98%86%E6%9B%B2", "getProject keywords=kunqu")
dump("https://www.ihchina.cn/getProject.html?province=110000", "getProject province=110000")
dump("https://www.ihchina.cn/art/representative.html?province=&rx_time=&type=&cate=&sex=&keywords=&limit=10&p=1", "representative limit10 p1")

print("\n### More endpoint guesses ###")
for u in ["https://www.ihchina.cn/getProject",
          "https://www.ihchina.cn/getProject.html?ajax=1&limit=100000&p=1",
          "https://www.ihchina.cn/index.php/getProject.html?limit=100000&p=1",
          "https://www.ihchina.cn/api/project?limit=100",
          "https://www.ihchina.cn/Project/index.html?limit=100",
          "https://www.ihchina.cn/project_list.html",
          "https://www.ihchina.cn/project/search?limit=100"]:
    st, hd, body = get(u, timeout=25)
    print(f"  {u} -> {st} {len(body)}B {hd.get('Content-Type')}")

print("\n### Same-origin JS bundles referenced by project.html ###")
st, hd, body = get("https://www.ihchina.cn/project.html")
t = body.decode("utf-8", "replace")
srcs = sorted(set(re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', t)))
print("  scripts:", srcs)
for s in srcs:
    if s.startswith("//"): s = "https:" + s
    elif s.startswith("/"): s = "https://www.ihchina.cn" + s
    elif not s.startswith("http"): continue
    st2, hd2, b2 = get(s, timeout=25)
    tt = b2.decode("utf-8", "replace")
    eps = sorted(set(re.findall(r'["\'](/(?:get|art|api|index)[A-Za-z_/]*\.html)["\']', tt)))
    print(f"  {s} -> {st2} {len(b2)}B endpoints={eps[:12]}")

print("\n### Detail page structure (project_details) ###")
st, hd, body = get("https://www.ihchina.cn/project_details/12178.html")
t = body.decode("utf-8", "replace")
plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
plain = re.sub(r"<[^>]+>", "|", plain)
plain = re.sub(r"[|\s]{2,}", "|", plain)
i = plain.find("项目")
print("  text window:", plain[max(0,i-100):i+500])
