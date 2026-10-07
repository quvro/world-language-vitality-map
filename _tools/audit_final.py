# -*- coding: utf-8 -*-
import re, json, time, io
import urllib.request, urllib.error

OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def get(url, timeout=60, headers=None):
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

def raw(repo, path, branch="master"):
    for br in [branch, "main"]:
        u = f"https://raw.githubusercontent.com/{repo}/{br}/{path}"
        st, hd, b = get(u, timeout=45)
        if st == 200:
            return u, b
    return u, b if st == 200 else b""

print("#" * 25, "TAROT: metabismuth/tarot-json", "#" * 25)
u, b = raw("metabismuth/tarot-json", "tarot.json")
P(f"  {u} -> {len(b)}B")
if b:
    try:
        j = json.loads(b.decode("utf-8", "replace"))
        P(f"  type={type(j).__name__} keys/len={list(j.keys()) if isinstance(j, dict) else len(j)}")
        P("  SAMPLE:", json.dumps(j, ensure_ascii=False)[:1500])
    except Exception as e:
        P("  parse err", e, b[:300])
u2, b2 = raw("metabismuth/tarot-json", "README.md")
P(f"  README: {b2.decode('utf-8','replace')[:900]}")

print("\n" + "#" * 25, "GREEK: burdiuz/mythology_demo_data", "#" * 25)
u, b = raw("burdiuz/mythology_demo_data", "genealogical_tree.json")
P(f"  {u} -> {len(b)}B")
if b:
    try:
        j = json.loads(b.decode("utf-8", "replace"))
        P(f"  top type={type(j).__name__} keys={list(j.keys())[:20] if isinstance(j, dict) else 'list len ' + str(len(j))}")
        s = json.dumps(j, ensure_ascii=False)
        P("  SAMPLE[:1200]:", s[:1200])
        n = len(re.findall(r'"name"', s))
        P(f"  approx person nodes (count of \"name\"): {n}")
    except Exception as e:
        P("  parse err", e, b[:400])

print("\n" + "#" * 25, "NORSE: swam92/datasetsProject data/Norse.csv", "#" * 25)
for path in ["data/Norse.csv", "data/norse.csv"]:
    u, b = raw("swam92/datasetsProject", path, branch="master")
    P(f"  {u} -> {len(b)}B")
    if b:
        t = b.decode("utf-8", "replace")
        P("  first 500:", t[:500].replace("\n", " | "))
        P("  lines:", len(t.splitlines()))
        break

print("\n" + "#" * 25, "SHANHAIJING: ZSLPZDZH beasts_data.json", "#" * 25)
u, b = raw("ZSLPZDZH/shanhaijing-bestiaire", "beasts_data.json", branch="main")
P(f"  {u} -> {len(b)}B")
if b:
    try:
        j = json.loads(b.decode("utf-8", "replace"))
        if isinstance(j, dict):
            P(f"  dict keys={list(j.keys())[:15]}")
            for k in list(j.keys())[:3]:
                if isinstance(j[k], list):
                    P(f"  {k}: list[{len(j[k])}] sample={json.dumps(j[k][0], ensure_ascii=False)[:600]}")
        elif isinstance(j, list):
            P(f"  list[{len(j)}] sample={json.dumps(j[0], ensure_ascii=False)[:700]}")
    except Exception as e:
        P("  parse err", e, b[:300])

print("\n" + "#" * 25, "TAROTOO dataset files", "#" * 25)
st, hd, b = get("https://api.github.com/repos/Tarotoo-com/tarotoo-tarot-dataset/contents/data",
                headers={"Accept": "application/vnd.github+json"})
P(f"  data/ listing -> {st}")
if st == 200:
    for i in json.loads(b.decode()):
        P(f"    {i['name']} {i['type']} {i.get('size')}")

print("\n" + "#" * 25, "WDQS: capture 429 body deliberately", "#" * 25)
UAQ = "KeshihuaCourseProject-DataSourceAudit/1.0 (university data-viz course)"
import random
for i in range(4):
    Q = f'SELECT (COUNT(?x) AS ?n) WHERE {{ ?x wdt:P31 wd:Q{random.randint(1000,99999)} . }}'
    u = "https://query.wikidata.org/sparql?format=json&query=" + urllib.request.quote(Q)
    st, hd, b = get(u, timeout=60, headers={"User-Agent": UAQ, "Accept": "application/sparql-results+json"})
    P(f"  q{i}: status={st} Retry-After={hd.get('Retry-After')} Age={hd.get('Age')} bytes={len(b)}")
    if st == 429:
        t = b.decode("utf-8", "replace")
        txt = re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", t, flags=re.S|re.I))
        txt = re.sub(r"\s+", " ", txt).strip()
        P("    429 BODY TEXT:", txt[:900])
        P("    RAW HEAD:", t[:400].replace("\n", " "))
        break
    time.sleep(0.5)

with open(r"E:\develop\myprogram\keshihua\_tools\results_final.txt", "w", encoding="utf-8") as f:
    f.write(OUT.getvalue())
print("\n[saved results_final.txt]")
