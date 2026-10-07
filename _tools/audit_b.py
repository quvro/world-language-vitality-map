# -*- coding: utf-8 -*-
import re, json, time
import urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=60, headers=None):
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

def strip(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

print("################ CTEXT.ORG ################")
for u in ["https://ctext.org/tools/api", "https://ctext.org/tools/api/zh", "https://ctext.org/",
          "https://ctext.org/shan-hai-jing/zh", "https://ctext.org/shan-hai-jing/zh?show=all"]:
    st, hd, b = get(u, timeout=50)
    print(f"\n--- {u}\n    status={st} bytes={len(b)} ctype={hd.get('Content-Type')} server={hd.get('Server')}")
    if st is None:
        print("    ERR:", b.decode("utf-8", "replace")[:300])
        continue
    t = b.decode("utf-8", "replace")
    print("    title:", (re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip()[:100] if re.search(r"<title>", t) else "?"))
    if "api" in u:
        s = strip(t)
        i = max(s.find("API"), 0)
        print("    TEXT:", s[max(0, i - 200):i + 2500])
    else:
        # count chapter links for shan-hai-jing
        links = re.findall(r'href="(/shan-hai-jing/[^"]+)"', t)
        print(f"    shan-hai-jing chapter links: {len(set(links))} e.g. {sorted(set(links))[:8]}")
        print("    TEXT[:300]:", strip(t)[:300])
    time.sleep(1)

print("\n################ ZH.WIKISOURCE ################")
for u in ["https://zh.wikisource.org/wiki/%E5%B1%B1%E6%B5%B7%E7%B6%93",
          "https://zh.wikisource.org/wiki/%E6%90%9C%E7%A5%9E%E8%A8%98",
          "https://zh.wikisource.org/wiki/%E8%81%8A%E9%BD%8B%E5%BF%97%E7%95%B0",
          "https://zh.wikisource.org/wiki/%E5%A4%AA%E5%B9%B3%E5%BB%A3%E8%A8%98"]:
    st, hd, b = get(u, timeout=50)
    t = b.decode("utf-8", "replace")
    print(f"\n--- {u}\n    status={st} bytes={len(b)}")
    if st == 200:
        print("    title:", (re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip()[:110] if re.search(r"<title>", t) else "?"))
        # chapter links
        ch = re.findall(r'href="(/wiki/[^"#]+)"[^>]*title="([^"]+)"', t)
        print(f"    internal links: {len(ch)}")
    time.sleep(0.6)

print("\n################ WIKISOURCE API: raw wikitext of 山海經 ################")
api = ("https://zh.wikisource.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main"
       "&format=json&titles=%E5%B1%B1%E6%B5%B7%E7%B6%93")
st, hd, b = get(api, timeout=50)
print(f"  status={st} bytes={len(b)}")
if st == 200:
    j = json.loads(b.decode("utf-8", "replace"))
    pages = j.get("query", {}).get("pages", {})
    for pid, p in pages.items():
        print(f"  pageid={pid} title={p.get('title')} missing={p.get('missing')}")
        rev = p.get("revisions", [{}])[0]
        content = rev.get("slots", {}).get("main", {}).get("*", "")
        print(f"  wikitext chars={len(content)}")
        print("  HEAD:", content[:900].replace("\n", " | "))

print("\n################ GITHUB SEARCH API ################")
def gh(q):
    u = "https://api.github.com/search/repositories?q=" + urllib.request.quote(q) + "&sort=stars&per_page=8"
    st, hd, b = get(u, timeout=45, headers={"Accept": "application/vnd.github+json"})
    print(f"\n=== q={q!r} -> status={st}")
    if st != 200:
        print("   ", b.decode("utf-8", "replace")[:300]); return
    j = json.loads(b.decode("utf-8", "replace"))
    print(f"    total_count={j.get('total_count')}")
    for it in j.get("items", []):
        print(f"    - {it['full_name']}  stars={it['stargazers_count']}  lic={(it.get('license') or {}).get('spdx_id')}")
        print(f"        {it['html_url']}")
        print(f"        desc: {(it.get('description') or '')[:150]}")

for q in ["shanhaijing", "山海经", "shan hai jing dataset", "搜神记", "聊斋志异"]:
    gh(q); time.sleep(3)
