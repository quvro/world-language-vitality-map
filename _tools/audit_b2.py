# -*- coding: utf-8 -*-
import re, json, time, sys, io
import urllib.request, urllib.error

OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.write(s + "\n")

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

print("### CTEXT.ORG retry (3 attempts each) ###")
for u in ["https://ctext.org/tools/api", "https://ctext.org/", "https://api.ctext.org/gettext?urn=ctp:shan-hai-jing/juan-1"]:
    for att in (1, 2, 3):
        st, hd, b = get(u, timeout=25)
        P(f"  {u} attempt{att} -> status={st} bytes={len(b)} {b[:90].decode('utf-8','replace') if st is None else ''}")
        if st is not None:
            break
        time.sleep(2)

print("\n### WIKISOURCE: chapter subpage listing + full text via API ###")
api_base = "https://zh.wikisource.org/w/api.php"
# list subpages of 山海經
u = api_base + "?action=query&list=allpages&apprefix=%E5%B1%B1%E6%B5%B7%E7%B6%93/&aplimit=50&format=json"
st, hd, b = get(u)
P(f"  allpages 山海經/ -> {st}")
if st == 200:
    j = json.loads(b.decode("utf-8", "replace"))
    pages = [p["title"] for p in j.get("query", {}).get("allpages", [])]
    P(f"    subpages({len(pages)}): {pages}")

# get full text of one chapter
u = (api_base + "?action=query&prop=extracts&explaintext=1&format=json&titles="
     + urllib.request.quote("山海經/卷一"))
st, hd, b = get(u)
if st == 200:
    j = json.loads(b.decode("utf-8", "replace"))
    for pid, p in j.get("query", {}).get("pages", {}).items():
        txt = p.get("extract", "")
        P(f"  extract 山海經/卷一: chars={len(txt)}")
        P("    HEAD:", txt[:400].replace("\n", " | "))

# how many chapters for each book
for book in ["山海經", "搜神記", "聊齋志異", "太平廣記"]:
    u = api_base + "?action=query&list=allpages&apprefix=" + urllib.request.quote(book + "/") + "&aplimit=500&format=json"
    st, hd, b = get(u)
    if st == 200:
        j = json.loads(b.decode("utf-8", "replace"))
        pages = j.get("query", {}).get("allpages", [])
        P(f"  {book}/ -> {len(pages)} subpages (limit500)  e.g. {[p['title'] for p in pages[:5]]}")
    time.sleep(1)

print("\n### GITHUB SEARCH API ###")
def gh(q):
    u = "https://api.github.com/search/repositories?q=" + urllib.request.quote(q) + "&sort=stars&per_page=8"
    st, hd, b = get(u, timeout=45, headers={"Accept": "application/vnd.github+json"})
    P(f"\n=== q={q!r} -> status={st}")
    if st != 200:
        P("   ", b.decode("utf-8", "replace")[:300]); return
    j = json.loads(b.decode("utf-8", "replace"))
    P(f"    total_count={j.get('total_count')}")
    for it in j.get("items", []):
        P(f"    - {it['full_name']} stars={it['stargazers_count']} lic={(it.get('license') or {}).get('spdx_id')} lang={it.get('language')}")
        P(f"      {it['html_url']}")
        P(f"      desc: {(it.get('description') or '')[:160]}")

for q in ["shanhaijing", "山海经", "搜神记", "聊斋志异", "tarot dataset"]:
    gh(q); time.sleep(4)

with open(r"E:\develop\myprogram\keshihua\_tools\results_b.txt", "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
print("\n[saved results_b.txt]")
