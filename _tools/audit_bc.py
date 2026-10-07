# -*- coding: utf-8 -*-
import re, json, time, io
import urllib.request, urllib.error

OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n")

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

def strip(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[ \t]+", " ", t).strip()

print("#" * 30, "CTEXT.ORG (retry until success)", "#" * 30)
for att in range(1, 9):
    st, hd, b = get("https://ctext.org/tools/api", timeout=30)
    P(f"attempt{att}: status={st} bytes={len(b)}")
    if st == 200 and len(b) > 500:
        t = b.decode("utf-8", "replace")
        P("  TITLE:", (re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip() if re.search(r"<title>", t) else "?"))
        P("  TEXT:", strip(t)[:2500])
        P("  RAW HEAD:", t[:1200].replace("\n", " "))
        break
    time.sleep(3)

print("\n" + "#" * 30, "WDQS FULL 429 BODY", "#" * 30)
Q = 'SELECT ?l WHERE { wd:Q178885 rdfs:label ?l FILTER(lang(?l)="en") }'
u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.request.quote(Q)
st, hd, b = get(u, timeout=45, headers={
    "User-Agent": "KeshihuaCourseProject-DataSourceAudit/1.0 (university data-viz course)",
    "Accept": "application/sparql-results+json"})
P(f"status={st} Retry-After={hd.get('Retry-After')} Content-Type={hd.get('Content-Type')} bytes={len(b)}")
t = b.decode("utf-8", "replace")
# extract the human-readable error message
for pat in [r"<h1[^>]*>(.*?)</h1>", r"<p[^>]*>(.*?)</p>", r"<div class=\"content-text\"[^>]*>(.*?)</div>"]:
    for m in re.findall(pat, t, re.S):
        s = strip(m)
        if len(s) > 20:
            P("   MSG:", s[:600])
P("  FULL TEXT:", strip(t)[:1500])

print("\n" + "#" * 30, "WIKISOURCE full-text proof", "#" * 30)
api = "https://zh.wikisource.org/w/api.php"
for title in ["山海經/南山經", "山海經/海外東經", "搜神記/第01卷", "聊齋志異/第01卷"]:
    u = api + "?action=query&prop=extracts&explaintext=1&format=json&titles=" + urllib.request.quote(title)
    st, hd, b = get(u)
    if st == 200:
        j = json.loads(b.decode("utf-8", "replace"))
        for pid, p in j.get("query", {}).get("pages", {}).items():
            txt = p.get("extract") or ""
            P(f"  {title}: chars={len(txt)} missing={'missing' in p}")
            if txt:
                P("      HEAD:", txt[:300].replace("\n", " | "))
    time.sleep(0.6)

print("\n" + "#" * 30, "GITHUB CANDIDATE REPOS", "#" * 30)
REPOS = [
    "metabismuth/tarot-json",
    "mixvlad/TarotCards",
    "Tarotoo-com/tarotoo-tarot-dataset",
    "ZSLPZDZH/shanhaijing-bestiaire",
    "yasenstar/shanhaijing",
    "waterkingest/Shanhaijing",
    "burdiuz/mythology_demo_data",
    "swam92/datasetsProject",
    "niltheory/GreekMythos",
]
for r in REPOS:
    st, hd, b = get(f"https://api.github.com/repos/{r}", headers={"Accept": "application/vnd.github+json"})
    if st != 200:
        P(f"\n--- {r}: API status={st} {b.decode('utf-8','replace')[:120]}")
        continue
    j = json.loads(b.decode())
    P(f"\n--- {j['full_name']}  stars={j['stargazers_count']}  license={(j.get('license') or {}).get('spdx_id')}  pushed={j.get('pushed_at')}  size={j.get('size')}KB  lang={j.get('language')}")
    P(f"    url: {j['html_url']}")
    P(f"    desc: {(j.get('description') or '')[:200]}")
    st2, hd2, b2 = get(f"https://api.github.com/repos/{r}/contents/", headers={"Accept": "application/vnd.github+json"})
    if st2 == 200:
        items = json.loads(b2.decode())
        P(f"    root files: {[(i['name'], i['type'], i.get('size')) for i in items][:25]}")
    time.sleep(1)

print("\n" + "#" * 30, "ihchina TYPE filter semantics", "#" * 30)
H = {"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.ihchina.cn/project.html"}
for q in ["type=%E6%B0%91%E9%97%B4%E6%96%87%E5%AD%A6", "cate=%E6%96%B0%E5%A2%9E%E9%A1%B9%E7%9B%AE",
          "rx_time=1", "rx_time=2006%E5%B9%B4", "sex=%E7%94%B7"]:
    u = f"https://www.ihchina.cn/getProject.html/?province=&rx_time=&type=&cate=&keywords=&category_id=16&limit=100000&p=1&{q}"
    st, hd, b = get(u, timeout=60, headers=H)
    try:
        j = json.loads(b.decode("utf-8", "replace"))
        P(f"  {q} -> total={j.get('total')} nrows={len(j.get('list') or [])}")
    except Exception:
        P(f"  {q} -> {st} {len(b)}B non-json")
    time.sleep(0.5)

with open(r"E:\develop\myprogram\keshihua\_tools\results_bc.txt", "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
print("\n[saved results_bc.txt]")
